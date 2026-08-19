import ast
import hashlib
import json
from pathlib import Path

import pytest

import scripts.external_signal_shadow.run_stage1_6a_futures_delisting_source_audit as runner
from scripts.external_signal_shadow.run_stage1_6a_futures_delisting_source_audit import (
    load_and_validate_bundle_records,
    run_source_audit,
    validate_capture_bundle_path,
)
from src.research.external_signal_shadow.stage1_6a_futures_delisting_storage import (
    load_completed_audit,
)


def test_runner_end_to_end_synthetic_fixture(tmp_path, monkeypatch):
    import src.research.external_signal_shadow.stage1_6a_futures_delisting_storage as storage

    bundle_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    output_parent = tmp_path / "data" / "external_signal_shadow" / "stage1_6a"
    output_parent.mkdir(parents=True)
    monkeypatch.setattr(storage, "STAGE1_6A_OUTPUT_PARENT", output_parent.resolve())
    out_dir = output_parent / "stage1_6a_e2e"

    completion_manifest_path = run_source_audit(
        capture_bundle_path=bundle_path,
        output_root=out_dir,
        fixture_run=True,
        run_id="e2e_001",
    )

    assert completion_manifest_path.exists()

    # Reload and verify with storage engine
    loaded = load_completed_audit(out_dir)
    assert loaded["completion_manifest"]["status"] == "complete"
    assert loaded["summary"]["fixture_run"] is True
    assert loaded["summary"]["source_audit_passed"] is False
    assert loaded["summary"]["live_trading_allowed"] is False


def test_runner_rejects_malformed_jsonl():
    malformed_bundle = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_malformed_capture_bundle.jsonl")
    with pytest.raises(ValueError, match="Malformed JSONL"):
        load_and_validate_bundle_records(malformed_bundle)


def test_runner_rejects_injected_derived_fields():
    injection_bundle = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_injection_attempt_bundle.jsonl")
    with pytest.raises(ValueError, match="Forbidden caller-injected derived fields"):
        load_and_validate_bundle_records(injection_bundle)


def test_runner_rejects_stage1_5_paths(tmp_path):
    bundle_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    forbidden_out = tmp_path / "stage1_5d" / "run"
    with pytest.raises(ValueError, match="Stage 1.6A output parent"):
        run_source_audit(bundle_path, forbidden_out, fixture_run=True)


def test_capture_bundle_path_is_confined_to_resolved_fixture_root(tmp_path, monkeypatch):
    fixture_root = tmp_path / "tests" / "fixtures" / "external_signal_shadow" / "stage1_6a"
    fixture_root.mkdir(parents=True)
    allowed = fixture_root / "allowed.jsonl"
    allowed.write_text('{"record_type":"list_capture"}\n', encoding="utf-8")
    outside = tmp_path / "outside.jsonl"
    outside.write_text('{"record_type":"list_capture"}\n', encoding="utf-8")
    escaped = fixture_root / "escaped.jsonl"
    escaped.symlink_to(outside)
    monkeypatch.setattr(runner, "FIXTURE_CAPTURE_ROOT", fixture_root.resolve())

    assert validate_capture_bundle_path(allowed) == allowed.resolve()
    with pytest.raises(ValueError, match="fixture root"):
        validate_capture_bundle_path(outside)
    with pytest.raises(ValueError, match="fixture root"):
        validate_capture_bundle_path(escaped)


def test_runner_requires_explicit_fixture_mode():
    bundle_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    with pytest.raises(ValueError, match="fixture-run"):
        run_source_audit(bundle_path, Path("data/external_signal_shadow/stage1_6a/not_used"), fixture_run=False)


def test_bundle_rejects_unknown_record_type_and_live_observed_provenance(tmp_path, monkeypatch):
    fixture_root = tmp_path / "tests" / "fixtures" / "external_signal_shadow" / "stage1_6a"
    fixture_root.mkdir(parents=True)
    monkeypatch.setattr(runner, "FIXTURE_CAPTURE_ROOT", fixture_root.resolve())

    unknown = fixture_root / "unknown.jsonl"
    unknown.write_text('{"record_type":"unexpected"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="record_type"):
        load_and_validate_bundle_records(unknown)

    live = fixture_root / "live.jsonl"
    live.write_text(
        '{"record_type":"list_capture","capture_mode":"live_observed"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="historical_backfill"):
        load_and_validate_bundle_records(live)


def test_fixture_manifest_records_each_fixture_sha256():
    fixture_root = Path("tests/fixtures/external_signal_shadow/stage1_6a")
    manifest = json.loads((fixture_root / "fixture_manifest.json").read_text(encoding="utf-8"))
    for filename, provenance in manifest["fixtures"].items():
        assert provenance["fixture_origin"] == "synthetic"
        assert provenance["capture_mode"] == "historical_backfill"
        assert provenance["sha256"] == hashlib.sha256((fixture_root / filename).read_bytes()).hexdigest()


def test_static_ast_isolation_and_no_network_or_trading_imports():
    """Verify Stage 1.6A files contain NO network libraries, NO Stage 1.5 runtime imports, and NO strategy/risk/execution wiring."""
    stage1_6a_files = [
        Path("src/research/external_signal_shadow/stage1_6a_futures_delisting_models.py"),
        Path("src/research/external_signal_shadow/stage1_6a_futures_delisting_audit.py"),
        Path("src/research/external_signal_shadow/stage1_6a_futures_delisting_summary.py"),
        Path("src/research/external_signal_shadow/stage1_6a_futures_delisting_storage.py"),
        Path("scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py"),
    ]

    forbidden_modules = {
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "urllib.request",
        "subprocess",
    }

    forbidden_prefixes = (
        "src.strategies",
        "src.risk",
        "src.execution",
        "src.research.external_signal_shadow.stage1_5d",
        "src.research.external_signal_shadow.stage1_5f",
        "src.research.external_signal_shadow.stage1_5g",
    )

    for file_path in stage1_6a_files:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden_modules, f"{file_path} imports forbidden module: {alias.name}"
                    for prefix in forbidden_prefixes:
                        assert not alias.name.startswith(prefix), f"{file_path} imports forbidden path: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert mod not in forbidden_modules, f"{file_path} imports from forbidden module: {mod}"
                for prefix in forbidden_prefixes:
                    assert not mod.startswith(prefix), f"{file_path} imports from forbidden path: {mod}"
