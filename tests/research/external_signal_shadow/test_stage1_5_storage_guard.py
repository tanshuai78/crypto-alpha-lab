"""Unit tests for Stage 1.5 Shared Storage Guard."""

import ast
import errno
import pathlib
import shutil
import tempfile

import pytest

from configs import base


def test_f_persistent_writers_do_not_create_fallback_guards():
    required_functions = {
        "src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py": {
            "append_jsonl",
            "write_json",
        },
        "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py": {
            "write_observer_root_contract_atomically",
            "emit_sample_capped_diagnostic",
            "process_schedule_revision_event",
            "reconcile_missing_accepted_rows",
            "reconcile_missing_terminal_ignored_rows",
            "reconcile_terminal_hygiene_artifacts",
        },
    }
    for path, names in required_functions.items():
        source = pathlib.Path(path).read_text(encoding="utf-8")
        functions = {
            node.name: node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name in names:
            node = functions[name]
            index = [arg.arg for arg in node.args.kwonlyargs].index("storage_guard")
            assert node.args.kw_defaults[index] is None
            assert "StorageGuard(" not in ast.get_source_segment(source, node)


def _outer_function_by_node(tree: ast.AST, node: ast.AST) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    outer = None
    current = node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            outer = current
    return outer


def _is_persistent_primitive(call: ast.Call) -> bool:
    if isinstance(call.func, ast.Attribute) and call.func.attr in {"write_text", "write_bytes", "replace"}:
        return True
    return (
        isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "os"
        and call.func.attr == "replace"
    )


def test_runner_has_no_guardless_persistent_writer_callsite():
    expected_primitive_owners = {
        "src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py": {
            "write_detail_retry_scheduler_state",
        },
        "src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py": {
            "write_detail_payload_append_only",
        },
        "src/research/external_signal_shadow/stage1_5d_runtime_gate.py": {
            "write_stage1_5d_runtime_gate_atomic",
        },
        "src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py": {
            "compact_observer_state_jsonl",
            "compact_event_batch_registry_jsonl",
        },
        "src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py": {
            "write_watermark_atomic",
        },
        "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py": {
            "write_smoke_summary_atomically",
        },
        "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py": {
            "write_live_depth_observer_summary_atomically",
            "write_observer_root_contract_atomically",
        },
    }

    for path, expected_owners in expected_primitive_owners.items():
        source = pathlib.Path(path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        owners = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_persistent_primitive(node):
                continue
            owner = _outer_function_by_node(tree, node)
            assert owner is not None, f"unguarded module-level writer in {path}:{node.lineno}"
            owners.add(owner.name)
            keyword_names = [arg.arg for arg in owner.args.kwonlyargs]
            assert "storage_guard" in keyword_names, f"missing guard in {path}:{owner.name}"
            guard_index = keyword_names.index("storage_guard")
            assert owner.args.kw_defaults[guard_index] is None, f"optional guard in {path}:{owner.name}"
            assert any(
                isinstance(call.func, ast.Attribute) and call.func.attr == "reserve_and_write"
                for call in ast.walk(owner)
                if isinstance(call, ast.Call)
            ), f"guard bypass in {path}:{owner.name}"
        assert owners == expected_owners


def test_no_storage_helper_contains_guard_none_direct_write_fallback():
    runner_paths = (
        "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py",
        "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py",
    )
    for path in runner_paths:
        source = pathlib.Path(path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "append_jsonl":
                continue
            assert any(
                keyword.arg == "storage_guard" and not isinstance(keyword.value, ast.Constant)
                for keyword in node.keywords
            ), f"guardless append_jsonl in {path}:{node.lineno}"


def test_persistent_writers_convert_guard_rejection_to_fail_closed_signal():
    expected_writers = {
        "src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py": {
            "write_detail_retry_scheduler_state",
        },
        "src/research/external_signal_shadow/stage1_5d_live_event_source_storage.py": {
            "append_jsonl",
            "write_detail_payload_append_only",
        },
        "src/research/external_signal_shadow/stage1_5d_runtime_gate.py": {
            "write_stage1_5d_runtime_gate_atomic",
        },
        "src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py": {
            "compact_observer_state_jsonl",
            "compact_event_batch_registry_jsonl",
            "update_batch_registry_status",
        },
        "src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py": {
            "append_jsonl",
            "write_json",
        },
        "src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py": {
            "write_watermark_atomic",
        },
        "src/research/external_signal_shadow/stage1_5f_schedule_revision_registry.py": {
            "record_revision",
        },
        "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py": {
            "write_smoke_summary_atomically",
        },
        "scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py": {
            "write_live_depth_observer_summary_atomically",
            "write_observer_root_contract_atomically",
        },
    }
    for path, names in expected_writers.items():
        source = pathlib.Path(path).read_text(encoding="utf-8")
        functions = {
            node.name: node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for name in names:
            assert "require_storage_write" in ast.get_source_segment(source, functions[name])


def test_storage_guard_constants_in_base_config():
    assert base.EXTERNAL_SIGNAL_STAGE1_5_HOST_START_FREE_BYTES == 8 * 1024 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5_HOST_RUNTIME_PROTECTED_RESERVE_BYTES == 4 * 1024 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5_HOST_ORDINARY_CONTROL_PLANE_RESERVE_BYTES == 52 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES == 12 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_ROOT_MAX_BYTES == 1 * 1024 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES == 12 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES == 4 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES == 2 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RAW_PAYLOAD_ROOT_MAX_BYTES == 768 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_ROOT_MAX_BYTES == 2 * 1024 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_ROOT_ORDINARY_CONTROL_PLANE_RESERVE_BYTES == 28 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_ROOT_EMERGENCY_BLOCKER_RESERVE_BYTES == 4 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES == 2 * 1024 * 1024
    assert base.EXTERNAL_SIGNAL_STAGE1_5_ROOT_RECONCILIATION_SCAN_INTERVAL_SEC == 300
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_CHECKPOINT_COMPACT_INTERVAL_SEC == 900
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_CHECKPOINT_COMPACT_THRESHOLD_BYTES == 256 * 1024 * 1024


def test_storage_guard_imports_and_reservation():
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir) / "stage1_5d_root"
        guard = StorageGuard(
            output_root=root,
            stage="1.5D",
            disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )

        res = guard.validate_startup()
        assert res["status"] == "ready"

        # Normal write
        write_res = guard.reserve_and_write(
            artifact_class="normal_data",
            transient_peak_bytes=100,
            persistent_delta_bytes=100,
            write_func=lambda: (root / "test.json").write_text("{}"),
        )
        assert write_res["status"] == "ready"
        assert write_res["written"] is True


def test_terminal_write_set_peak_counts_prior_persistent_artifacts():
    from src.research.external_signal_shadow.stage1_5_storage_guard import (
        terminal_write_set_peak_bytes,
    )

    assert terminal_write_set_peak_bytes([b"gate", b"summary", b"diagnostic"]) == len(b"gate") + len(b"summary") + len(b"diagnostic")


def test_write_oserror_becomes_fail_closed_storage_result(tmp_path):
    from src.research.external_signal_shadow.stage1_5_storage_guard import (
        StorageGuard,
        StorageWriteBlocked,
        require_storage_write,
    )

    guard = StorageGuard(
        output_root=tmp_path,
        stage="1.5D",
        disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
    )

    result = guard.reserve_and_write(
        artifact_class="normal_data",
        transient_peak_bytes=1,
        persistent_delta_bytes=1,
        write_func=lambda: (_ for _ in ()).throw(OSError(errno.ENOSPC, "No space left on device")),
    )

    assert result["status"] == "blocked_write_oserror"
    assert result["written"] is False
    assert result["storage_blocker"] == "write_oserror_errno_28"
    with pytest.raises(StorageWriteBlocked, match="write_oserror_errno_28"):
        require_storage_write(guard, result)


def test_host_emergency_reserve_covers_actual_d_plus_f_peaks(tmp_path):
    from scripts.external_signal_shadow import (
        run_stage1_5d_live_event_source_smoke_collector as d_runner,
    )
    from scripts.external_signal_shadow import run_stage1_5f_live_depth_observer as f_runner

    d_gate, d_summary, d_diagnostic = d_runner._build_storage_failure_artifacts(
        tmp_path / "stage1_5d",
        "x" * 512,
        "x" * 128,
    )
    d_peak = d_runner._storage_failure_write_set_peak(d_gate, d_summary, d_diagnostic)
    f_peak = f_runner._storage_failure_write_set_peak(
        f_runner._build_storage_failure_summary("x" * 512, "x" * 128)
    )

    assert d_peak + f_peak <= base.EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES


def test_startup_rejects_host_emergency_smaller_than_d_plus_f_terminal_caps(tmp_path, monkeypatch):
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    monkeypatch.setattr(
        base,
        "EXTERNAL_SIGNAL_STAGE1_5_HOST_EMERGENCY_BLOCKER_RESERVE_BYTES",
        base.EXTERNAL_SIGNAL_STAGE1_5D_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        + base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
        - 1,
    )
    guard = StorageGuard(
        output_root=tmp_path,
        stage="1.5D",
        disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
    )

    assert guard.validate_startup()["status"] == "blocked_start_host_terminal_reserve"


def test_normal_write_denied_when_near_reserve():
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir) / "stage1_5d_root"
        root.mkdir(parents=True, exist_ok=True)
        # Create dummy file to simulate root usage near limit (1GiB - 15MiB)
        # Root limit = 1GiB (1073741824), Ordinary reserve = 12MiB, Emergency reserve = 4MiB
        # Max normal data accounted = 1GiB - 12MiB - 4MiB = 1057423360
        guard = StorageGuard(
            output_root=root,
            stage="1.5D",
            disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )
        guard._accounted_root_bytes = 1057423360  # Exactly at the limit

        res = guard.reserve_and_write(
            artifact_class="normal_data",
            transient_peak_bytes=100,
            persistent_delta_bytes=100,
            write_func=lambda: None,
        )
        assert res["status"] == "blocked_root_budget"
        assert res["written"] is False


def test_ordinary_write_allowed_in_ordinary_reserve_but_denied_in_emergency():
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard


    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir) / "stage1_5d_root"
        root.mkdir(parents=True, exist_ok=True)
        guard = StorageGuard(
            output_root=root,
            stage="1.5D",
            disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )
        # Accounted root bytes inside ordinary reserve range
        guard._accounted_root_bytes = 1058000000

        # Ordinary control plane write allowed
        res = guard.reserve_and_write(
            artifact_class="ordinary_control_plane",
            transient_peak_bytes=100,
            persistent_delta_bytes=100,
            write_func=lambda: None,
        )
        assert res["status"] == "ready"

        # Near emergency reserve (1GiB - 4MiB = 1069547520)
        guard._accounted_root_bytes = 1069547520
        res2 = guard.reserve_and_write(
            artifact_class="ordinary_control_plane",
            transient_peak_bytes=100,
            persistent_delta_bytes=100,
            write_func=lambda: None,
        )
        assert res2["status"] == "blocked_root_budget"


def test_terminal_write_allowed_in_emergency_reserve():
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir) / "stage1_5d_root"
        root.mkdir(parents=True, exist_ok=True)
        guard = StorageGuard(
            output_root=root,
            stage="1.5D",
            disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
        )
        guard._accounted_root_bytes = 1069547520  # Inside emergency reserve range

        res = guard.reserve_and_write(
            artifact_class="terminal_control_plane",
            transient_peak_bytes=100,
            persistent_delta_bytes=100,
            write_func=lambda: None,
        )
        assert res["status"] == "ready"


def test_terminal_write_larger_than_configured_cap_is_blocked_before_write(tmp_path):
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    guard = StorageGuard(
        output_root=tmp_path,
        stage="1.5D",
        disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
    )
    called = False

    def write_func():
        nonlocal called
        called = True

    result = guard.reserve_and_write(
        artifact_class="terminal_control_plane",
        transient_peak_bytes=guard.terminal_write_set_cap_bytes + 1,
        persistent_delta_bytes=guard.terminal_write_set_cap_bytes + 1,
        write_func=write_func,
    )
    assert result["status"] == "blocked_terminal_peak_exceeded"
    assert result["written"] is False
    assert called is False


def test_startup_validation_rejects_excessive_terminal_peak():
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    with tempfile.TemporaryDirectory() as tmpdir:
        root = pathlib.Path(tmpdir) / "stage1_5d_root"
        guard = StorageGuard(
            output_root=root,
            stage="1.5D",
            disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
            terminal_write_set_peak_bytes=3 * 1024 * 1024,  # Exceeds 2MiB limit
        )

        res = guard.validate_startup()
        assert res["status"] == "blocked_start_terminal_peak_exceeded"
