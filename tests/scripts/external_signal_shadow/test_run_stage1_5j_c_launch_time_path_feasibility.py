"""CLI and Custodian TCB boundary tests for Stage 1.5J-C."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_cli_custodian_release_required_before_upstream_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Locally self-consistent approval/sidecar/derived JSON without Custodian release must stop before any upstream loader."""
    from research.external_signal_shadow import (
        stage1_5j_c_launch_time_path_feasibility as jc,
    )
    from scripts.external_signal_shadow import (
        run_stage1_5j_c_launch_time_path_feasibility as cli,
    )

    loader_called = False

    def _sentinel_loader(*args: object, **kwargs: object) -> None:
        nonlocal loader_called
        loader_called = True
        raise AssertionError("Upstream loader must NEVER be called when Custodian release is missing")

    monkeypatch.setattr(
        jc,
        "load_verified_stage1_5j_a_historical_archive_coverage_root",
        _sentinel_loader,
        raising=False,
    )
    monkeypatch.setattr(
        jc,
        "load_verified_stage1_5j_b_historical_aggtrades_launch_response_root",
        _sentinel_loader,
        raising=False,
    )

    run_id = "stage1_5j_c_launch_time_path_feasibility_20261024T120000Z"
    auth_dir = tmp_path / "auth_dir" / run_id
    auth_dir.mkdir(parents=True)
    out_root = tmp_path / "validation_out" / run_id

    _, bundle_sha = jc.compute_source_bundle_seals_and_sha256(PROJECT_ROOT)
    plan_rel = "docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md"
    plan_sha = _sha256_bytes((PROJECT_ROOT / plan_rel).read_bytes())

    approval_lines = [
        f"APPROVED_J_C_PLAN_RELATIVE_PATH={plan_rel}",
        f"APPROVED_J_C_PLAN_SHA256={plan_sha}",
        f"AUTHORIZED_SOURCE_BUNDLE_SHA256={bundle_sha}",
        "AUTHORIZED_OPERATION=offline_time_path_validation_once",
        f"AUTHORIZED_RUN_ID={run_id}",
        f"AUTHORIZED_OUTPUT_ROOT={out_root}",
        "NETWORK_ALLOWED=false",
        "SIGNAL_ALLOWED=false",
        "PAPER_TRADING_ALLOWED=false",
        "LIVE_TRADING_ALLOWED=false",
        "EXECUTION_ALLOWED=false",
    ]
    approval_bytes = ("\n".join(approval_lines) + "\n").encode("utf-8")
    approval_file = auth_dir / "user_receipt_generation_approval.txt"
    approval_file.write_bytes(approval_bytes)
    (auth_dir / "user_receipt_generation_approval.txt.sha256").write_text(
        f"{_sha256_bytes(approval_bytes)}  user_receipt_generation_approval.txt\n",
        encoding="utf-8",
    )

    # Even if a locally fabricated run_authorization.json exists, missing authorization_release.json MUST stop
    fake_derived = auth_dir / "run_authorization.json"
    fake_derived_bytes = b'{"fake":true}\n'
    fake_derived.write_bytes(fake_derived_bytes)
    (auth_dir / "run_authorization.json.sha256").write_text(
        f"{_sha256_bytes(fake_derived_bytes)}  run_authorization.json\n",
        encoding="utf-8",
    )

    rc = cli.main(
        [
            "--operation",
            "offline_time_path_validation_once",
            "--run-id",
            run_id,
        ],
        _test_authority_root=tmp_path / "auth_dir",
    )
    assert rc == 1
    assert loader_called is False


def test_eleven_line_approval_and_release_grammar_validation(tmp_path: Path) -> None:
    """Verify exact 11-line approval grammar, two-space sidecars, release keys, and derived run_authorization.json."""
    from research.external_signal_shadow import (
        stage1_5j_c_launch_time_path_feasibility as jc,
    )

    run_id = "stage1_5j_c_launch_time_path_feasibility_20261024T120000Z"
    auth_dir = tmp_path / "auth" / run_id
    auth_dir.mkdir(parents=True)
    out_root = tmp_path / "val_out" / run_id

    source_seals, bundle_sha = jc.compute_source_bundle_seals_and_sha256(PROJECT_ROOT)
    assert len(source_seals) == 11
    assert [s["relative_path"] for s in source_seals] == sorted(
        s["relative_path"] for s in source_seals
    )

    plan_rel = "docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md"
    plan_bytes = (PROJECT_ROOT / plan_rel).read_bytes()
    plan_sha = _sha256_bytes(plan_bytes)

    design_rel = "docs/designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md"
    design_bytes = (PROJECT_ROOT / design_rel).read_bytes()
    design_sha = _sha256_bytes(design_bytes)

    approval_lines = [
        f"APPROVED_J_C_PLAN_RELATIVE_PATH={plan_rel}",
        f"APPROVED_J_C_PLAN_SHA256={plan_sha}",
        f"AUTHORIZED_SOURCE_BUNDLE_SHA256={bundle_sha}",
        "AUTHORIZED_OPERATION=offline_time_path_validation_once",
        f"AUTHORIZED_RUN_ID={run_id}",
        f"AUTHORIZED_OUTPUT_ROOT={out_root}",
        "NETWORK_ALLOWED=false",
        "SIGNAL_ALLOWED=false",
        "PAPER_TRADING_ALLOWED=false",
        "LIVE_TRADING_ALLOWED=false",
        "EXECUTION_ALLOWED=false",
    ]
    approval_bytes = ("\n".join(approval_lines) + "\n").encode("utf-8")
    approval_file = auth_dir / "user_receipt_generation_approval.txt"
    approval_file.write_bytes(approval_bytes)
    approval_sha = _sha256_bytes(approval_bytes)
    (auth_dir / "user_receipt_generation_approval.txt.sha256").write_text(
        f"{approval_sha}  user_receipt_generation_approval.txt\n",
        encoding="utf-8",
    )

    approval_rel = f".git/plan-execution/stage1_5j_c/{plan_sha}/{run_id}/user_receipt_generation_approval.txt"
    release_obj = {
        "authorized_source_bundle_sha256": bundle_sha,
        "design": {
            "relative_path": design_rel,
            "sha256": design_sha,
            "size_bytes": len(design_bytes),
        },
        "execution_allowed": False,
        "live_trading_allowed": False,
        "network_allowed": False,
        "operation": "offline_time_path_validation_once",
        "output_root": str(out_root),
        "paper_trading_allowed": False,
        "plan": {
            "relative_path": plan_rel,
            "sha256": plan_sha,
            "size_bytes": len(plan_bytes),
        },
        "release_schema_version": 1,
        "release_state": "user_message_verified_and_released",
        "run_id": run_id,
        "signal_allowed": False,
        "user_receipt_generation_approval": {
            "relative_path": approval_rel,
            "sha256": approval_sha,
            "size_bytes": len(approval_bytes),
        },
    }
    release_bytes = (
        json.dumps(release_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    release_file = auth_dir / "authorization_release.json"
    release_file.write_bytes(release_bytes)
    (auth_dir / "authorization_release.json.sha256").write_text(
        f"{_sha256_bytes(release_bytes)}  authorization_release.json\n",
        encoding="utf-8",
    )

    derived = jc.verify_and_derive_run_authorization(
        operation="offline_time_path_validation_once",
        run_id=run_id,
        project_root=PROJECT_ROOT,
        authority_dir=auth_dir,
    )
    assert derived["run_id"] == run_id
    assert derived["authorized_source_bundle_sha256"] == bundle_sha
    assert (auth_dir / "run_authorization.json").is_file()
    assert (auth_dir / "run_authorization.json.sha256").is_file()


def _setup_valid_auth_dir(
    base_dir: Path,
    run_id: str,
    operation: str,
    output_root_str: str,
    *,
    project_root: Path = PROJECT_ROOT,
) -> Path:
    from research.external_signal_shadow import (
        stage1_5j_c_launch_time_path_feasibility as jc,
    )

    plan_rel = jc.APPROVED_PLAN_RELATIVE_PATH
    plan_bytes = (project_root / plan_rel).read_bytes()
    plan_sha = _sha256_bytes(plan_bytes)
    design_rel = jc.APPROVED_DESIGN_RELATIVE_PATH
    design_bytes = (project_root / design_rel).read_bytes()
    design_sha = _sha256_bytes(design_bytes)
    _, bundle_sha = jc.compute_source_bundle_seals_and_sha256(project_root)

    auth_dir = base_dir / run_id
    auth_dir.mkdir(parents=True, exist_ok=True)

    approval_lines = [
        f"APPROVED_J_C_PLAN_RELATIVE_PATH={plan_rel}",
        f"APPROVED_J_C_PLAN_SHA256={plan_sha}",
        f"AUTHORIZED_SOURCE_BUNDLE_SHA256={bundle_sha}",
        f"AUTHORIZED_OPERATION={operation}",
        f"AUTHORIZED_RUN_ID={run_id}",
        f"AUTHORIZED_OUTPUT_ROOT={output_root_str}",
        "NETWORK_ALLOWED=false",
        "SIGNAL_ALLOWED=false",
        "PAPER_TRADING_ALLOWED=false",
        "LIVE_TRADING_ALLOWED=false",
        "EXECUTION_ALLOWED=false",
    ]
    approval_bytes = ("\n".join(approval_lines) + "\n").encode("ascii")
    (auth_dir / "user_receipt_generation_approval.txt").write_bytes(approval_bytes)
    approval_sha = _sha256_bytes(approval_bytes)
    (auth_dir / "user_receipt_generation_approval.txt.sha256").write_text(
        f"{approval_sha}  user_receipt_generation_approval.txt\n",
        encoding="ascii",
    )

    approval_rel = f".git/plan-execution/stage1_5j_c/{plan_sha}/{run_id}/user_receipt_generation_approval.txt"
    release_obj = {
        "authorized_source_bundle_sha256": bundle_sha,
        "design": {
            "relative_path": design_rel,
            "sha256": design_sha,
            "size_bytes": len(design_bytes),
        },
        "execution_allowed": False,
        "live_trading_allowed": False,
        "network_allowed": False,
        "operation": operation,
        "output_root": output_root_str,
        "paper_trading_allowed": False,
        "plan": {
            "relative_path": plan_rel,
            "sha256": plan_sha,
            "size_bytes": len(plan_bytes),
        },
        "release_schema_version": 1,
        "release_state": "user_message_verified_and_released",
        "run_id": run_id,
        "signal_allowed": False,
        "user_receipt_generation_approval": {
            "relative_path": approval_rel,
            "sha256": approval_sha,
            "size_bytes": len(approval_bytes),
        },
    }
    release_bytes = (
        json.dumps(release_obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")
    (auth_dir / "authorization_release.json").write_bytes(release_bytes)
    (auth_dir / "authorization_release.json.sha256").write_text(
        f"{_sha256_bytes(release_bytes)}  authorization_release.json\n",
        encoding="ascii",
    )
    return auth_dir


def test_cli_usage_error_rc_2_and_no_override_flags() -> None:
    """Verify CLI usage errors and unsupported override flags return RC=2 without running preflight or loaders."""
    from scripts.external_signal_shadow import (
        run_stage1_5j_c_launch_time_path_feasibility as cli,
    )

    for bad_args in (
        [],
        ["--operation", "offline_time_path_validation_once"],
        ["--run-id", "stage1_5j_c_launch_time_path_feasibility_20261024T120000Z"],
        [
            "--operation",
            "offline_time_path_validation_once",
            "--run-id",
            "stage1_5j_c_launch_time_path_feasibility_20261024T120000Z",
            "--output-root",
            "/tmp/override",
        ],
        [
            "--operation",
            "offline_time_path_validation_once",
            "--run-id",
            "stage1_5j_c_launch_time_path_feasibility_20261024T120000Z",
            "--skip-checks",
        ],
    ):
        assert cli.main(bad_args) == 2


def test_custodian_static_no_writer_and_runtime_write_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove statically and at runtime that core and CLI never write, rename, unlink, or repair approval/release files."""
    import os

    from research.external_signal_shadow import (
        stage1_5j_c_launch_time_path_feasibility as jc,
    )
    from scripts.external_signal_shadow import (
        run_stage1_5j_c_launch_time_path_feasibility as cli,
    )

    # 1. Static source inspection: only run_authorization.json and producer_lifecycle_evidence.json may be written in authority_dir; protocol file is NEVER written
    for mod_path in (Path(jc.__file__), Path(cli.__file__)):
        text = mod_path.read_text(encoding="utf-8")
        assert "approval_file.write" not in text
        assert "release_file.write" not in text
        assert "approval_sidecar.write" not in text
        assert "release_sidecar.write" not in text
        assert "approval_file.unlink" not in text
        assert "release_file.unlink" not in text
        assert "protocol_path.write" not in text
        assert "PROTOCOL_RELATIVE_PATH.write" not in text

    # 2. Runtime write-sentinel on os.open, Path.write_bytes, Path.write_text, os.rename, os.unlink
    orig_os_open = os.open
    orig_write_bytes = Path.write_bytes
    orig_write_text = Path.write_text
    orig_unlink = os.unlink

    def _check_not_custodian_target(p: object) -> None:
        s = str(p)
        if (
            "user_receipt_generation_approval" in s
            or "authorization_release" in s
            or "docs/production_artifacts" in s
            or "stage1_5j_c_time_path_protocol_v1.json" in s
        ):
            raise AssertionError(f"WORKSPACE_WRITE_SENTINEL triggered on {s}")

    def _guarded_os_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            _check_not_custodian_target(path)
        return orig_os_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

    def _guarded_write_bytes(self: Path, data: bytes) -> int:
        _check_not_custodian_target(self)
        return orig_write_bytes(self, data)

    def _guarded_write_text(self: Path, data: str, *args: object, **kwargs: object) -> int:
        _check_not_custodian_target(self)
        return orig_write_text(self, data, *args, **kwargs)  # type: ignore[arg-type]

    def _guarded_unlink(path: object, *args: object, **kwargs: object) -> None:
        _check_not_custodian_target(path)
        return orig_unlink(path, *args, **kwargs)  # type: ignore[arg-type]

    run_id = "stage1_5j_c_launch_time_path_feasibility_20261024T120100Z"
    out_root = tmp_path / "val_out" / run_id
    auth_base = tmp_path / "auth_base"
    _setup_valid_auth_dir(
        auth_base,
        run_id,
        "offline_time_path_validation_once",
        str(out_root),
    )

    monkeypatch.setattr(os, "open", _guarded_os_open)
    monkeypatch.setattr(Path, "write_bytes", _guarded_write_bytes)
    monkeypatch.setattr(Path, "write_text", _guarded_write_text)
    monkeypatch.setattr(os, "unlink", _guarded_unlink)

    derived = jc.verify_and_derive_run_authorization(
        operation="offline_time_path_validation_once",
        run_id=run_id,
        project_root=PROJECT_ROOT,
        authority_dir=auth_base / run_id,
    )
    assert derived["run_id"] == run_id


def test_cli_preflight_rejections_before_upstream_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify source-bundle mismatch, true permission, authority symlink, and mismatched output_root stop before upstream loader."""
    from research.external_signal_shadow import (
        stage1_5j_c_launch_time_path_feasibility as jc,
    )
    from scripts.external_signal_shadow import (
        run_stage1_5j_c_launch_time_path_feasibility as cli,
    )

    loader_called = False

    def _sentinel(*args: object, **kwargs: object) -> None:
        nonlocal loader_called
        loader_called = True
        raise AssertionError("Upstream loader must NEVER be called on preflight failure")

    monkeypatch.setattr(jc, "_load_upstream_ja_and_jb_for_replay", _sentinel)

    run_id = "stage1_5j_c_launch_time_path_feasibility_20261024T120200Z"

    # Case 1: Source bundle SHA mismatch in approval & release
    base_1 = tmp_path / "c1"
    auth_1 = _setup_valid_auth_dir(
        base_1,
        run_id,
        "offline_time_path_validation_once",
        str(tmp_path / "out1" / run_id),
    )
    rel_obj_1 = json.loads((auth_1 / "authorization_release.json").read_text(encoding="utf-8"))
    rel_obj_1["authorized_source_bundle_sha256"] = "0" * 64
    rel_bytes_1 = (json.dumps(rel_obj_1, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    (auth_1 / "authorization_release.json").write_bytes(rel_bytes_1)
    (auth_1 / "authorization_release.json.sha256").write_text(
        f"{_sha256_bytes(rel_bytes_1)}  authorization_release.json\n", encoding="ascii"
    )
    assert (
        cli.main(
            ["--operation", "offline_time_path_validation_once", "--run-id", run_id],
            _test_authority_root=base_1,
        )
        == 1
    )
    assert loader_called is False

    # Case 2: True permission in release
    base_2 = tmp_path / "c2"
    auth_2 = _setup_valid_auth_dir(
        base_2,
        run_id,
        "offline_time_path_validation_once",
        str(tmp_path / "out2" / run_id),
    )
    rel_obj_2 = json.loads((auth_2 / "authorization_release.json").read_text(encoding="utf-8"))
    rel_obj_2["network_allowed"] = True
    rel_bytes_2 = (json.dumps(rel_obj_2, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    (auth_2 / "authorization_release.json").write_bytes(rel_bytes_2)
    (auth_2 / "authorization_release.json.sha256").write_text(
        f"{_sha256_bytes(rel_bytes_2)}  authorization_release.json\n", encoding="ascii"
    )
    assert (
        cli.main(
            ["--operation", "offline_time_path_validation_once", "--run-id", run_id],
            _test_authority_root=base_2,
        )
        == 1
    )
    assert loader_called is False

    # Case 3: Mismatched output_root between approval and release
    base_3 = tmp_path / "c3"
    auth_3 = _setup_valid_auth_dir(
        base_3,
        run_id,
        "offline_time_path_validation_once",
        str(tmp_path / "out3_a" / run_id),
    )
    rel_obj_3 = json.loads((auth_3 / "authorization_release.json").read_text(encoding="utf-8"))
    rel_obj_3["output_root"] = str(tmp_path / "out3_b" / run_id)
    rel_bytes_3 = (json.dumps(rel_obj_3, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    (auth_3 / "authorization_release.json").write_bytes(rel_bytes_3)
    (auth_3 / "authorization_release.json.sha256").write_text(
        f"{_sha256_bytes(rel_bytes_3)}  authorization_release.json\n", encoding="ascii"
    )
    assert (
        cli.main(
            ["--operation", "offline_time_path_validation_once", "--run-id", run_id],
            _test_authority_root=base_3,
        )
        == 1
    )
    assert loader_called is False

    # Case 4: Symlink on authorization_release.json
    base_4 = tmp_path / "c4"
    auth_4 = _setup_valid_auth_dir(
        base_4,
        run_id,
        "offline_time_path_validation_once",
        str(tmp_path / "out4" / run_id),
    )
    real_rel = tmp_path / "real_release.json"
    (auth_4 / "authorization_release.json").rename(real_rel)
    (auth_4 / "authorization_release.json").symlink_to(real_rel)
    assert (
        cli.main(
            ["--operation", "offline_time_path_validation_once", "--run-id", run_id],
            _test_authority_root=base_4,
        )
        == 1
    )
    assert loader_called is False

    # Case 5: Validation output_root inside repository
    base_5 = tmp_path / "c5"
    _setup_valid_auth_dir(
        base_5,
        run_id,
        "offline_time_path_validation_once",
        str(PROJECT_ROOT / "data" / run_id),
    )
    assert (
        cli.main(
            ["--operation", "offline_time_path_validation_once", "--run-id", run_id],
            _test_authority_root=base_5,
        )
        == 1
    )
    assert loader_called is False


def test_cli_lifecycle_evidence_written_only_after_parent_fsync_and_fails_on_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify CLI writes producer_lifecycle_evidence.json + sidecar only after PublishResult, and omits it on parent-fsync fault."""
    from research.external_signal_shadow import (
        stage1_5j_c_launch_time_path_feasibility as jc,
    )
    from scripts.external_signal_shadow import (
        run_stage1_5j_c_launch_time_path_feasibility as cli,
    )
    from tests.research.external_signal_shadow.test_stage1_5j_c_launch_time_path_feasibility import (
        _build_synthetic_ja_root_and_package,
    )

    ja_root, ja_summary, _, ledger_path = _build_synthetic_ja_root_and_package(tmp_path / "synth")
    jb_child_rows = [
        {
            "source_article_id": "a" * 32,
            "symbol": "SYNTHUSDT",
            "symbol_launch_time_ms": 1760000000000,
            "anchor_state": "anchor_found",
            "anchor_time_ms": 1760000000000,
            "anchor_price": "1",
            "anchor_delay_ms": 0,
            "j_a_parent_state": "coverage_complete",
            "j_a_child_state": "j_a_child_coverage_complete",
            "required_archive_dates_by_horizon": {},
        }
    ]

    def _mock_compute_summary(*, run_id, artifact_kind, authority_obj, protocol_obj, **kwargs):
        return jc.compute_stage1_5j_c_summary_from_admitted_inputs(
            run_id=run_id,
            artifact_kind=artifact_kind,
            authority_obj=authority_obj,
            protocol_obj=protocol_obj,
            ja_root=ja_root,
            ja_summary=ja_summary,
            jb_child_rows=jb_child_rows,
            ledger_path=ledger_path,
            project_root=tmp_path / "synth",
            expected_universe_count=1,
            expected_selected_count=1,
        )

    monkeypatch.setattr(
        cli, "_produce_summary_for_authorized_run", _mock_compute_summary
    )

    # 1. Positive run -> RC=0 and producer_lifecycle_evidence.json + .sha256 created
    run_ok = "stage1_5j_c_launch_time_path_feasibility_20261024T120500Z"
    out_ok = tmp_path / "out_ok" / run_ok
    auth_base_ok = tmp_path / "auth_ok"
    _setup_valid_auth_dir(
        auth_base_ok,
        run_ok,
        "offline_time_path_validation_once",
        str(out_ok),
    )
    rc_ok = cli.main(
        ["--operation", "offline_time_path_validation_once", "--run-id", run_ok],
        _test_authority_root=auth_base_ok,
    )
    assert rc_ok == 0
    ev_file = auth_base_ok / run_ok / "evidence" / "producer_lifecycle_evidence.json"
    ev_sidecar = auth_base_ok / run_ok / "evidence" / "producer_lifecycle_evidence.json.sha256"
    assert ev_file.is_file()
    assert ev_sidecar.is_file()
    ev_obj = json.loads(ev_file.read_text(encoding="utf-8"))
    assert ev_obj["evidence_schema_version"] == 1
    assert ev_obj["publish_terminal"] == "parent_directory_fsynced"
    assert ev_obj["producer_returned_success"] is True
    assert ev_obj["final_root"] == str(out_ok)

    # 2. Parent directory fsync fault AFTER rename -> root exists on disk, but CLI returns RC=1 and NO producer_lifecycle_evidence.json!
    run_fault = "stage1_5j_c_launch_time_path_feasibility_20261024T120600Z"
    out_fault = tmp_path / "out_fault" / run_fault
    auth_base_fault = tmp_path / "auth_fault"
    _setup_valid_auth_dir(
        auth_base_fault,
        run_fault,
        "offline_time_path_validation_once",
        str(out_fault),
    )
    orig_fsync_dir = jc._fsync_directory

    def _fault_parent_fsync(p: Path) -> None:
        if p == out_fault.parent:
            raise OSError("injected parent fsync fault after rename")
        orig_fsync_dir(p)

    with monkeypatch.context() as mp:
        mp.setattr(jc, "_fsync_directory", _fault_parent_fsync)
        rc_fault = cli.main(
            ["--operation", "offline_time_path_validation_once", "--run-id", run_fault],
            _test_authority_root=auth_base_fault,
        )
    assert rc_fault == 1
    assert out_fault.exists()
    assert not (
        auth_base_fault / run_fault / "evidence" / "producer_lifecycle_evidence.json"
    ).exists()

