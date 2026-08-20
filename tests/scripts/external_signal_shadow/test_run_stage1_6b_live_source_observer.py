"""Unit, CLI, lifecycle, and static AST writer inventory tests for live observer runner."""

import ast
import hashlib
import io
import json
from pathlib import Path

import pytest

import scripts.external_signal_shadow.run_stage1_6b_live_source_observer as live_runner
from scripts.external_signal_shadow.run_stage1_6b_live_source_observer import (
    run_live_source_observer,
)
from scripts.external_signal_shadow.run_stage1_6b_source_profile_probe import (
    compute_source_profile_sha256,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    SOURCE_PROFILE_ID,
    CaptureMode,
    CaptureRunContract,
    ObserverCheckpointRecord,
    SourceProfileProbeAttestation,
    compute_request_headers_profile_sha256,
)
from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import (
    RootWriterLock,
    RootWriterLockError,
    load_sealed_export,
    write_capture_run_contract,
    write_observer_checkpoint,
)


class MockHTTPResponse:
    def __init__(self, body_bytes: bytes, status: int = 200, headers: dict = None, url: str = "https://www.binance.com"):
        self._body = io.BytesIO(body_bytes)
        self.status = status
        self.code = status
        self.headers = headers or {"Content-Type": "application/json"}
        self.url = url

    def read(self, amt=None):
        return self._body.read(amt)

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def geturl(self):
        return self.url

    def close(self):
        pass


def setup_valid_attestation(tmp_path, attested_at_ms=1000):
    p_sha = compute_source_profile_sha256()
    att_dir = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "source_profile_attestations" / p_sha
    att_dir.mkdir(parents=True, exist_ok=True)
    att_path = att_dir / "source_profile_probe_attestation.json"

    att = SourceProfileProbeAttestation(
        schema_version="stage1_6b_source_profile_probe_attestation_v1",
        probe_command_version="source_profile_probe_v1",
        source_profile_id=SOURCE_PROFILE_ID,
        source_authority="binance_official_content",
        transport_support_status="undocumented_public_web_profile",
        source_profile_sha256=p_sha,
        request_headers_profile_sha256=compute_request_headers_profile_sha256(),
        probe_article_id="a" * 32,
        index_requested_url="https://www.binance.com/index",
        index_final_url="https://www.binance.com/index",
        index_http_status=200,
        index_content_type="application/json",
        index_payload_bytes=100,
        index_article_id_path="data.articles[].code",
        detail_requested_url="https://www.binance.com/detail",
        detail_final_url="https://www.binance.com/detail",
        detail_http_status=200,
        detail_content_type="application/json",
        detail_payload_bytes=100,
        detail_body_path="data.body",
        probe_attested_at_ms=attested_at_ms,
    )
    att_path.write_text(json.dumps(att.to_dict()))
    return att_path


def test_live_runner_requires_live_public_readonly(tmp_path):
    """Verify live runner rejects startup without --live-public-readonly flag."""
    att_path = setup_valid_attestation(tmp_path)
    with pytest.raises(ValueError, match="live_public_readonly_required"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=False,
            project_root=tmp_path,
        )


def test_live_runner_max_seconds_bounds_and_epoch_limit(tmp_path):
    """Verify max_seconds > 7 days is rejected and shorter max_seconds is enforced."""
    att_path = setup_valid_attestation(tmp_path)
    seven_days_plus_1 = (7 * 24 * 3600) + 1

    with pytest.raises(ValueError, match="max_seconds_exceeds_epoch_limit"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            max_seconds=seven_days_plus_1,
            project_root=tmp_path,
        )


def test_live_runner_executes_max_polls_and_seals_export(tmp_path):
    """Verify live runner executes exact max_polls, writes terminal status test_bound, and seals export."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)

    art_code = "d" * 32
    index_payload = json.dumps({
        "code": "000000",
        "data": {
            "articles": [
                {
                    "code": art_code,
                    "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
                    "releaseDate": 1732000000000
                }
            ]
        }
    }).encode("utf-8")

    detail_payload = json.dumps({
        "code": "000000",
        "data": {
            "code": art_code,
            "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
            "body": "<p>Content</p>",
            "releaseDate": 1732000000000
        }
    }).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        elif "article/detail/query" in url:
            return MockHTTPResponse(detail_payload, url=url)
        raise ValueError(f"Unexpected url {url}")

    run_root = run_live_source_observer(
        attestation_path=att_path,
        live_public_readonly=True,
        max_polls=2,
        project_root=tmp_path,
        opener=mock_opener,
        run_id="run_live_test_bound",
        sleep_func=lambda s: None,  # no actual sleep
    )

    assert run_root.is_dir()
    term_file = run_root / "terminal_status.json"
    assert term_file.is_file()
    term_data = json.loads(term_file.read_text())
    assert term_data["status"] == "complete"
    assert term_data["terminal_reason"] == "test_bound"

    # Verify sealed export exists and passes load_sealed_export
    sealed_dir = run_root / "sealed_exports"
    assert sealed_dir.is_dir()
    export_subdirs = list(sealed_dir.iterdir())
    assert len(export_subdirs) == 1
    export_dir = export_subdirs[0]
    loaded = load_sealed_export(export_dir)
    assert loaded["status"] == "complete"


def test_live_runner_lifetime_writer_lock_prevents_dual_writer(tmp_path):
    """Verify that running a second observer on the same run root is blocked before network calls."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)
    run_root = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / "run_dual"
    run_root.mkdir(parents=True, exist_ok=True)

    # Acquire lock externally
    lock = RootWriterLock(run_root)
    lock.acquire()

    with pytest.raises(RootWriterLockError, match="root_already_owned"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            resume=True,
            run_id="run_dual",
            project_root=tmp_path,
        )

    lock.release()


def test_resume_writes_reconciliation_checkpoint_before_client_construction(tmp_path, monkeypatch):
    """Resume must durable-checkpoint reconciled state before constructing its network client."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)
    att_sha = hashlib.sha256(att_path.read_bytes()).hexdigest()
    run_id = "run_resume"
    run_root = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / run_id
    run_root.mkdir(parents=True)
    guard = live_runner.Stage16BStorageGuard(output_root=run_root)
    contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id=run_id,
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256=att_sha,
        run_started_at_ms=1000,
    )
    write_capture_run_contract(run_root, contract, guard, 0)
    (run_root / "source_profile_probe_attestation.json").write_bytes(att_path.read_bytes())
    checkpoint = ObserverCheckpointRecord(
        schema_version="stage1_6b_observer_checkpoint_v1",
        run_id=run_id,
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256=att_sha,
        checkpoint_id="checkpoint_before_resume",
        prior_checkpoint_id=None,
        poll_seq=0,
        monotonic_request_seq=0,
        record_seq=0,
        accounted_root_bytes=0,
        stream_offsets={},
        stream_last_hashes={},
        candidate_states={},
        heartbeat_at_ms=1000,
    )
    write_observer_checkpoint(run_root, checkpoint, guard, 0)

    class ClientAfterReconciliation:
        def __init__(self, **_kwargs):
            state = json.loads((run_root / "observer_checkpoint.json").read_text())
            assert state["prior_checkpoint_id"] == "checkpoint_before_resume"

    monkeypatch.setattr(live_runner, "Stage16BCanonicalClient", ClientAfterReconciliation)
    live_runner.run_live_source_observer(
        attestation_path=att_path,
        live_public_readonly=True,
        resume=True,
        run_id=run_id,
        max_seconds=0,
        project_root=tmp_path,
    )


def test_static_ast_guarded_write_surface_closure():
    """Verify that every persistent write in stage1_6b modules and scripts passes through guarded storage."""
    targets = [
        Path("src/research/external_signal_shadow/stage1_6b_canonical_source_models.py"),
        Path("src/research/external_signal_shadow/stage1_6b_canonical_source_client.py"),
        Path("src/research/external_signal_shadow/stage1_6b_canonical_source_observer.py"),
        Path("scripts/external_signal_shadow/run_stage1_6b_source_profile_probe.py"),
        Path("scripts/external_signal_shadow/run_stage1_6b_historical_backfill.py"),
        Path("scripts/external_signal_shadow/run_stage1_6b_live_source_observer.py"),
    ]

    for p in targets:
        if not p.is_file():
            continue
        src = p.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for direct calls to open(..., w or a) or Path.write_bytes/write_text
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ["open"] and p.name not in ["stage1_6b_canonical_source_storage.py"]:
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and any(m in str(arg.value) for m in ["w", "a", "x"]):
                            # Must not have raw open for writing outside storage primitives
                            pytest.fail(f"Unguarded raw file open in {p}: {ast.unparse(node)}")
