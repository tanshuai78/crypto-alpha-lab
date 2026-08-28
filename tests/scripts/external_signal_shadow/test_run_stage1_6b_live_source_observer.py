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
    compute_live_v3_checkpoint_id,
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
    def __init__(
        self,
        body_bytes: bytes,
        status: int = 200,
        headers: dict = None,
        url: str = "https://www.binance.com",
    ):
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
    att_dir = (
        tmp_path
        / "data"
        / "external_signal_shadow"
        / "stage1_6b"
        / "source_profile_attestations"
        / p_sha
    )
    att_dir.mkdir(parents=True, exist_ok=True)
    att_path = att_dir / "source_profile_probe_attestation.json"

    att = SourceProfileProbeAttestation(
        schema_version="stage1_6b_source_profile_probe_attestation_v2",
        probe_command_version="source_profile_probe_v2",
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
        index_article_id_path='data.catalogs[?catalogId==161 && catalogName=="Delisting"].articles[].code',
        detail_requested_url="https://www.binance.com/detail",
        detail_final_url="https://www.binance.com/detail",
        detail_http_status=200,
        detail_content_type="application/json",
        detail_payload_bytes=100,
        detail_body_path="data.body",
        probe_attested_at_ms=attested_at_ms,
        selected_catalog_id=161,
        selected_catalog_name="Delisting",
        selected_catalog_article_count=1,
    )
    att_path.write_text(json.dumps(att.to_dict()))
    return att_path


def test_live_observer_rejects_v1_probe_attestation_pre_network(tmp_path):
    """Task 3.4: Live runner rejects v1 probe attestation before client/opener construction."""
    p_sha = compute_source_profile_sha256()
    att_dir = (
        tmp_path
        / "data"
        / "external_signal_shadow"
        / "stage1_6b"
        / "source_profile_attestations"
        / p_sha
    )
    att_dir.mkdir(parents=True, exist_ok=True)
    att_path = att_dir / "source_profile_probe_attestation.json"

    att_v1 = {
        "schema_version": "stage1_6b_source_profile_probe_attestation_v1",
        "probe_command_version": "source_profile_probe_v1",
        "source_profile_id": "binance_public_web_bapi_en_v1",
        "source_authority": "binance_official_content",
        "transport_support_status": "undocumented_public_web_profile",
        "source_profile_sha256": "dummy_sha",
        "request_headers_profile_sha256": compute_request_headers_profile_sha256(),
        "probe_article_id": "a" * 32,
        "index_requested_url": "https://www.binance.com/index",
        "index_final_url": "https://www.binance.com/index",
        "index_http_status": 200,
        "index_content_type": "application/json",
        "index_payload_bytes": 100,
        "index_article_id_path": "data.articles[].code",
        "detail_requested_url": "https://www.binance.com/detail",
        "detail_final_url": "https://www.binance.com/detail",
        "detail_http_status": 200,
        "detail_content_type": "application/json",
        "detail_payload_bytes": 100,
        "detail_body_path": "data.body",
        "probe_attested_at_ms": 1000,
    }
    att_path.write_text(json.dumps(att_v1))

    opener_called = []

    def mock_opener(req, timeout=10.0):
        opener_called.append(req)
        return MockHTTPResponse(b"{}")

    with pytest.raises(ValueError, match="attestation"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            project_root=tmp_path,
            opener=mock_opener,
        )

    assert len(opener_called) == 0
    live_root = tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation"
    assert not live_root.exists()


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
    index_payload = json.dumps(
        {
            "code": "000000",
            "data": {
                "catalogs": [
                    {
                        "catalogId": 161,
                        "catalogName": "Delisting",
                        "total": 426,
                        "articles": [
                            {
                                "code": art_code,
                                "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
                                "releaseDate": 1732000000000,
                            }
                        ],
                    }
                ]
            },
        }
    ).encode("utf-8")

    detail_payload = json.dumps(
        {
            "code": "000000",
            "data": {
                "code": art_code,
                "title": "Binance Futures Will Delist USDⓈ-M UNIFI Perpetual Contract at 2024-11-25 09:00 (UTC)",
                "body": "<p>Content</p>",
                "releaseDate": 1732000000000,
            },
        }
    ).encode("utf-8")

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
    run_root = (
        tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / "run_dual"
    )
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
    run_root = (
        tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / run_id
    )
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
    chk_raw = {
        "schema_version": "stage1_6b_observer_checkpoint_v3",
        "run_id": run_id,
        "capture_mode": CaptureMode.LIVE_OBSERVED.value,
        "source_profile_id": SOURCE_PROFILE_ID,
        "source_profile_attestation_sha256": att_sha,
        "prior_checkpoint_id": None,
        "poll_seq": 0,
        "monotonic_request_seq": 0,
        "record_seq": 0,
        "accounted_root_bytes": 0,
        "stream_offsets": {},
        "stream_last_hashes": {},
        "candidate_states": {},
        "heartbeat_at_ms": 1000,
        "last_index_poll_status": "trusted",
        "last_index_poll_coverage": "successful",
        "pending_terminal_failure_reason": None,
    }
    chk_id = compute_live_v3_checkpoint_id(chk_raw)
    checkpoint = ObserverCheckpointRecord(**dict(chk_raw, checkpoint_id=chk_id))
    write_observer_checkpoint(run_root, checkpoint, guard, 0)

    class ClientAfterReconciliation:
        def __init__(self, **_kwargs):
            state = json.loads((run_root / "observer_checkpoint.json").read_text())
            assert state["prior_checkpoint_id"] == chk_id

    monkeypatch.setattr(live_runner, "Stage16BCanonicalClient", ClientAfterReconciliation)
    live_runner.run_live_source_observer(
        attestation_path=att_path,
        live_public_readonly=True,
        resume=True,
        run_id=run_id,
        max_seconds=0,
        project_root=tmp_path,
    )


def test_resume_rejects_legacy_profile_contract_before_reconciliation_or_network(tmp_path):
    """A legacy-profile contract cannot authorize a v2 resume root."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)
    att_sha = hashlib.sha256(att_path.read_bytes()).hexdigest()
    run_id = "run_legacy_contract"
    run_root = (
        tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / run_id
    )
    run_root.mkdir(parents=True)
    guard = live_runner.Stage16BStorageGuard(output_root=run_root)
    legacy_contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id=run_id,
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id="binance_public_web_bapi_en_v1",
        source_profile_attestation_sha256=att_sha,
        run_started_at_ms=1000,
    )
    write_capture_run_contract(run_root, legacy_contract, guard, 0)
    (run_root / "source_profile_probe_attestation.json").write_bytes(att_path.read_bytes())
    checkpoint = ObserverCheckpointRecord(
        schema_version="stage1_6b_observer_checkpoint_v2",
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
        last_index_poll_status="trusted",
        last_index_poll_coverage="successful",
    )
    write_observer_checkpoint(run_root, checkpoint, guard, 0)
    before = sum(path.stat().st_size for path in run_root.rglob("*") if path.is_file())
    opener_calls = []

    with pytest.raises(ValueError, match="cannot_resume_run_contract_or_attestation_mismatch"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            resume=True,
            run_id=run_id,
            project_root=tmp_path,
            opener=lambda *args, **kwargs: opener_calls.append((args, kwargs)),
        )

    assert opener_calls == []
    assert sum(path.stat().st_size for path in run_root.rglob("*") if path.is_file()) == before


@pytest.mark.parametrize(
    ("stream_rel", "v1_row", "v2_row", "error"),
    [
        (
            "list_captures/2026-08-22.jsonl",
            {"schema_version": "stage1_6b_list_capture_v1", "source_profile_id": SOURCE_PROFILE_ID},
            {
                "schema_version": "stage1_6b_list_capture_v2",
                "source_profile_id": SOURCE_PROFILE_ID,
                "selected_catalog_id": 161,
                "selected_catalog_name": "Delisting",
                "selected_catalog_total": 1,
                "article_count": 1,
            },
            "list_capture_v2_required",
        ),
        (
            "article_discoveries.jsonl",
            {
                "schema_version": "stage1_6b_article_discovery_v1",
                "source_profile_id": SOURCE_PROFILE_ID,
            },
            {
                "schema_version": "stage1_6b_article_discovery_v2",
                "source_profile_id": SOURCE_PROFILE_ID,
                "source_catalog_id": 161,
                "source_catalog_name": "Delisting",
            },
            "article_discovery_v2_required",
        ),
    ],
)
def test_resume_rejects_mixed_v1_v2_committed_prefix_before_network(
    tmp_path,
    stream_rel,
    v1_row,
    v2_row,
    error,
):
    """Every parsed committed row must be v2 before resume can write or construct a client."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)
    att_sha = hashlib.sha256(att_path.read_bytes()).hexdigest()
    run_id = f"run_mixed_{stream_rel.split('/')[0]}"
    run_root = (
        tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / run_id
    )
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
    stream_path = run_root / stream_rel
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    stream_path.write_text(json.dumps(v1_row) + "\n" + json.dumps(v2_row) + "\n")
    chk_raw = {
        "schema_version": "stage1_6b_observer_checkpoint_v3",
        "run_id": run_id,
        "capture_mode": CaptureMode.LIVE_OBSERVED.value,
        "source_profile_id": SOURCE_PROFILE_ID,
        "source_profile_attestation_sha256": att_sha,
        "prior_checkpoint_id": None,
        "poll_seq": 0,
        "monotonic_request_seq": 0,
        "record_seq": 0,
        "accounted_root_bytes": 0,
        "stream_offsets": {stream_rel: stream_path.stat().st_size},
        "stream_last_hashes": {
            stream_rel: hashlib.sha256(json.dumps(v2_row).encode("utf-8")).hexdigest()
        },
        "candidate_states": {},
        "heartbeat_at_ms": 1000,
        "last_index_poll_status": "trusted",
        "last_index_poll_coverage": "successful",
        "pending_terminal_failure_reason": None,
    }
    chk_id = compute_live_v3_checkpoint_id(chk_raw)
    checkpoint = ObserverCheckpointRecord(**dict(chk_raw, checkpoint_id=chk_id))
    write_observer_checkpoint(run_root, checkpoint, guard, 0)

    before = sum(path.stat().st_size for path in run_root.rglob("*") if path.is_file())
    opener_calls = []

    with pytest.raises(ValueError, match=error):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            resume=True,
            run_id=run_id,
            project_root=tmp_path,
            opener=lambda *args, **kwargs: opener_calls.append((args, kwargs)),
        )

    assert opener_calls == []
    assert sum(path.stat().st_size for path in run_root.rglob("*") if path.is_file()) == before


def test_live_runner_schema_drift_terminal_failure_and_no_sealed_export(tmp_path):
    """Task 4.4: Live runner catches schema drift, records terminal failure, and produces no sealed export."""
    from scripts.external_signal_shadow.run_stage1_6b_live_source_observer import (
        LiveObserverRunnerError,
    )

    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)

    malformed_index = json.dumps(
        {
            "code": "000000",
            "data": {
                "catalogs": [
                    {"catalogId": 999, "catalogName": "WrongCatalog", "articles": [], "total": 0}
                ]
            },
        }
    ).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        return MockHTTPResponse(malformed_index, url=req.get_full_url())

    with pytest.raises(LiveObserverRunnerError, match="source_profile_schema_drift"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            max_polls=1,
            project_root=tmp_path,
            opener=mock_opener,
            run_id="run_live_drift",
            sleep_func=lambda s: None,
        )

    run_root = (
        tmp_path
        / "data"
        / "external_signal_shadow"
        / "stage1_6b"
        / "live_observation"
        / "run_live_drift"
    )
    assert run_root.is_dir()

    term_file = run_root / "terminal_status.json"
    assert term_file.is_file()
    term_data = json.loads(term_file.read_text())
    assert term_data["status"] == "failure"
    assert term_data["terminal_reason"] == "source_profile_schema_drift"
    checkpoint_data = json.loads((run_root / "observer_checkpoint.json").read_text())
    assert checkpoint_data["pending_terminal_failure_reason"] == "source_profile_schema_drift"
    assert checkpoint_data["checkpoint_id"] == term_data["final_checkpoint_id"]

    # Sealed exports must NOT exist
    assert not (run_root / "sealed_exports").exists()

    # Subsequent resume must reject before any opener call
    opener_called = []

    def mock_opener_resume(req, timeout=10.0):
        opener_called.append(req)
        return MockHTTPResponse(b"{}")

    with pytest.raises(Exception):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            resume=True,
            run_id="run_live_drift",
            project_root=tmp_path,
            opener=mock_opener_resume,
        )
    assert len(opener_called) == 0


def test_live_runner_deadline_missed_writes_intent_checkpoint_and_terminal_failure(tmp_path):
    """Task 4.1: Runner catches SLA deadline missed, writes intent checkpoint and failure terminal status, and leaves unsealed."""
    from scripts.external_signal_shadow.run_stage1_6b_live_source_observer import (
        LiveObserverRunnerError,
    )
    from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
        CandidateState,
        compute_live_v3_checkpoint_id,
    )

    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)
    att_sha = hashlib.sha256(att_path.read_bytes()).hexdigest()

    run_id = "run_live_sla_fail"
    run_root_dir = (
        tmp_path / "data" / "external_signal_shadow" / "stage1_6b" / "live_observation" / run_id
    )
    run_root_dir.mkdir(parents=True)
    guard = live_runner.Stage16BStorageGuard(output_root=run_root_dir)

    contract = CaptureRunContract(
        schema_version="stage1_6b_capture_run_contract_v1",
        run_id=run_id,
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_profile_attestation_sha256=att_sha,
        run_started_at_ms=1000,
    )
    write_capture_run_contract(run_root_dir, contract, guard, 0)
    (run_root_dir / "source_profile_probe_attestation.json").write_bytes(att_path.read_bytes())

    # Candidate admitted at poll 1 with deadline 1, but still unattempted entering poll 2
    cand = CandidateState(
        source_article_id="a" * 32,
        first_discovered_poll_seq=1,
        first_discovered_at_ms=1000,
        lane="lane_a",
        detail_attempt_count=0,
        retry_cycle_count=0,
        first_attempt_at_ms=None,
        last_attempt_at_ms=None,
        next_retry_at_ms=None,
        terminal_reason=None,
        trusted_detail_revision_id=None,
        first_attempt_ahead_count_at_admission=0,
        first_attempt_deadline_poll_seq=1,
    )
    chk_raw = {
        "schema_version": "stage1_6b_observer_checkpoint_v3",
        "run_id": run_id,
        "capture_mode": CaptureMode.LIVE_OBSERVED.value,
        "source_profile_id": SOURCE_PROFILE_ID,
        "source_profile_attestation_sha256": att_sha,
        "prior_checkpoint_id": None,
        "poll_seq": 1,
        "monotonic_request_seq": 1,
        "record_seq": 1,
        "accounted_root_bytes": 0,
        "stream_offsets": {},
        "stream_last_hashes": {},
        "candidate_states": {"a" * 32: cand.to_dict("stage1_6b_observer_checkpoint_v3")},
        "heartbeat_at_ms": 1000,
        "last_index_poll_status": "trusted",
        "last_index_poll_coverage": "successful",
        "pending_terminal_failure_reason": None,
    }
    chk_id = compute_live_v3_checkpoint_id(chk_raw)
    checkpoint = ObserverCheckpointRecord(**dict(chk_raw, checkpoint_id=chk_id))
    write_observer_checkpoint(run_root_dir, checkpoint, guard, 0)

    index_payload = json.dumps(
        {
            "code": "000000",
            "data": {
                "catalogs": [
                    {
                        "catalogId": 161,
                        "catalogName": "Delisting",
                        "total": 1,
                        "articles": [
                            {"code": "a" * 32, "title": "Delist Token", "releaseDate": 1000}
                        ],
                    }
                ]
            },
        }
    ).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        return MockHTTPResponse(b'{"code":"000000","data":{"body":"ok"}}', url=url)

    with pytest.raises(LiveObserverRunnerError, match="detail_first_attempt_deadline_missed"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            resume=True,
            max_polls=1,
            project_root=tmp_path,
            opener=mock_opener,
            run_id=run_id,
            sleep_func=lambda s: None,
        )

    assert run_root_dir.is_dir()
    term_file = run_root_dir / "terminal_status.json"
    assert term_file.is_file()
    term_data = json.loads(term_file.read_text())
    assert term_data["status"] == "failure"
    assert term_data["terminal_reason"] == "detail_first_attempt_deadline_missed"
    assert not (run_root_dir / "sealed_exports").exists()

    # Checkpoint has failure intent
    chk_file = run_root_dir / "observer_checkpoint.json"
    assert chk_file.is_file()
    chk_data = json.loads(chk_file.read_text())
    assert chk_data["pending_terminal_failure_reason"] == "detail_first_attempt_deadline_missed"
    assert chk_data["checkpoint_id"] == term_data["final_checkpoint_id"]


def test_live_runner_capacity_exceeded_writes_intent_checkpoint_and_terminal_failure(
    tmp_path, monkeypatch
):
    """Task 4.2: Runner catches candidate capacity exceeded, writes intent checkpoint and failure terminal status."""
    from configs import base
    from scripts.external_signal_shadow.run_stage1_6b_live_source_observer import (
        LiveObserverRunnerError,
    )

    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES", 2)

    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)

    articles = [
        {
            "code": f"{i:032x}",
            "title": f"Binance Futures Will Delist Token_{i}",
            "releaseDate": 1732000000000,
        }
        for i in range(1, 5)  # 4 articles > capacity 2
    ]
    index_payload = json.dumps(
        {
            "code": "000000",
            "data": {
                "catalogs": [
                    {
                        "catalogId": 161,
                        "catalogName": "Delisting",
                        "total": 4,
                        "articles": articles,
                    }
                ]
            },
        }
    ).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        return MockHTTPResponse(b'{"code":"100000","message":"fail"}', url=url)

    run_root_dir = (
        tmp_path
        / "data"
        / "external_signal_shadow"
        / "stage1_6b"
        / "live_observation"
        / "run_live_cap_fail"
    )

    with pytest.raises(LiveObserverRunnerError, match="pending_detail_candidate_capacity_exceeded"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            max_polls=1,
            project_root=tmp_path,
            opener=mock_opener,
            run_id="run_live_cap_fail",
            sleep_func=lambda s: None,
        )

    assert run_root_dir.is_dir()
    term_file = run_root_dir / "terminal_status.json"
    assert term_file.is_file()
    term_data = json.loads(term_file.read_text())
    assert term_data["status"] == "failure"
    assert term_data["terminal_reason"] == "pending_detail_candidate_capacity_exceeded"
    assert not (run_root_dir / "sealed_exports").exists()


def test_live_runner_storage_blocked_writes_emergency_terminal_failure(tmp_path, monkeypatch):
    """Task 4.3: Runner catches Stage16BStorageBlocked, writes emergency failure terminal status, and leaves unsealed."""
    from scripts.external_signal_shadow.run_stage1_6b_live_source_observer import (
        LiveObserverRunnerError,
    )
    from src.research.external_signal_shadow.stage1_6b_canonical_source_storage import (
        Stage16BStorageBlocked,
    )

    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)

    articles = [
        {
            "code": "a" * 32,
            "title": "Binance Futures Will Delist TokenA",
            "releaseDate": 1732000000000,
        }
    ]
    index_payload = json.dumps(
        {
            "code": "000000",
            "data": {
                "catalogs": [
                    {
                        "catalogId": 161,
                        "catalogName": "Delisting",
                        "total": 1,
                        "articles": articles,
                    }
                ]
            },
        }
    ).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        return MockHTTPResponse(b'{"code":"000000","data":{"body":"ok"}}', url=url)

    # Monkeypatch admitted_write to fail on normal_data writes
    orig_admitted = live_runner.Stage16BStorageGuard.admitted_write

    def mock_admitted_write(self, write_class, *args, **kwargs):
        if write_class == "normal_data":
            raise Stage16BStorageBlocked("root_budget_exceeded", "simulated root budget overflow")
        return orig_admitted(self, write_class, *args, **kwargs)

    monkeypatch.setattr(live_runner.Stage16BStorageGuard, "admitted_write", mock_admitted_write)

    run_root_dir = (
        tmp_path
        / "data"
        / "external_signal_shadow"
        / "stage1_6b"
        / "live_observation"
        / "run_live_storage_fail"
    )

    with pytest.raises(LiveObserverRunnerError, match="storage_exhausted"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            max_polls=1,
            project_root=tmp_path,
            opener=mock_opener,
            run_id="run_live_storage_fail",
            sleep_func=lambda s: None,
        )

    assert run_root_dir.is_dir()
    term_file = run_root_dir / "terminal_status.json"
    assert term_file.is_file()
    term_data = json.loads(term_file.read_text())
    assert term_data["status"] == "failure"
    assert term_data["terminal_reason"] == "storage_exhausted"
    checkpoint_data = json.loads((run_root_dir / "observer_checkpoint.json").read_text())
    assert checkpoint_data["pending_terminal_failure_reason"] == "storage_exhausted"
    assert checkpoint_data["checkpoint_id"] == term_data["final_checkpoint_id"]
    assert not (run_root_dir / "sealed_exports").exists()


def test_live_runner_writes_terminal_when_failure_intent_write_is_blocked(tmp_path, monkeypatch):
    """A blocked ordinary intent write cannot consume the terminal reserve path."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)

    def raise_deadline(self, now_ms=None):
        raise live_runner.ObserverSLAError("deadline missed")

    def block_intent(self, now_ms, failure_reason):
        raise live_runner.Stage16BStorageBlocked("root_budget_exceeded", "intent blocked")

    monkeypatch.setattr(live_runner.Stage16BObserver, "execute_poll", raise_deadline)
    monkeypatch.setattr(
        live_runner.Stage16BObserver,
        "write_failure_intent_checkpoint",
        block_intent,
    )

    with pytest.raises(live_runner.LiveObserverRunnerError, match="detail_first_attempt_deadline_missed"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            max_polls=1,
            project_root=tmp_path,
            run_id="run_intent_blocked",
            sleep_func=lambda _: None,
        )

    root = (
        tmp_path
        / "data"
        / "external_signal_shadow"
        / "stage1_6b"
        / "live_observation"
        / "run_intent_blocked"
    )
    terminal = json.loads((root / "terminal_status.json").read_text())
    assert terminal["status"] == "failure"
    assert terminal["terminal_reason"] == "detail_first_attempt_deadline_missed"
    assert terminal["final_checkpoint_id"] is None
    assert not (root / "sealed_exports").exists()


def test_live_runner_unknown_sla_code_writes_no_false_terminal(tmp_path, monkeypatch):
    """Only the approved deadline code may create the deadline failure terminal."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)
    intent_calls = []

    def raise_unknown(self, now_ms=None):
        raise live_runner.ObserverSLAError("unknown SLA", code="unmapped_sla_code")

    def unexpected_intent(self, now_ms, failure_reason):
        intent_calls.append(failure_reason)
        raise AssertionError("unknown SLA code must not write failure intent")

    monkeypatch.setattr(live_runner.Stage16BObserver, "execute_poll", raise_unknown)
    monkeypatch.setattr(
        live_runner.Stage16BObserver,
        "write_failure_intent_checkpoint",
        unexpected_intent,
    )

    with pytest.raises(live_runner.LiveObserverRunnerError, match="unmapped_sla_code"):
        run_live_source_observer(
            attestation_path=att_path,
            live_public_readonly=True,
            max_polls=1,
            project_root=tmp_path,
            run_id="run_unknown_sla",
            sleep_func=lambda _: None,
        )

    root = (
        tmp_path
        / "data"
        / "external_signal_shadow"
        / "stage1_6b"
        / "live_observation"
        / "run_unknown_sla"
    )
    assert intent_calls == []
    assert not (root / "terminal_status.json").exists()


def test_live_runner_keyboard_interrupt_writes_operator_stop_unsealed(tmp_path):
    """Task 4.4: SIGINT/KeyboardInterrupt gracefully writes operator_stop terminal status without sealing."""
    att_path = setup_valid_attestation(tmp_path, attested_at_ms=1000)

    articles = [
        {
            "code": "a" * 32,
            "title": "Binance Futures Will Delist TokenA",
            "releaseDate": 1732000000000,
        }
    ]
    index_payload = json.dumps(
        {
            "code": "000000",
            "data": {
                "catalogs": [
                    {
                        "catalogId": 161,
                        "catalogName": "Delisting",
                        "total": 1,
                        "articles": articles,
                    }
                ]
            },
        }
    ).encode("utf-8")

    def mock_opener(req, timeout=10.0):
        url = req.get_full_url()
        if "article/list/query" in url:
            return MockHTTPResponse(index_payload, url=url)
        return MockHTTPResponse(b'{"code":"000000","data":{"body":"ok"}}', url=url)

    def raise_interrupt(sec):
        raise KeyboardInterrupt("simulated operator stop")

    run_root_dir = run_live_source_observer(
        attestation_path=att_path,
        live_public_readonly=True,
        max_polls=5,
        project_root=tmp_path,
        opener=mock_opener,
        run_id="run_live_sigint",
        sleep_func=raise_interrupt,
    )

    assert run_root_dir.is_dir()
    term_file = run_root_dir / "terminal_status.json"
    assert term_file.is_file()
    term_data = json.loads(term_file.read_text())
    assert term_data["status"] == "complete"
    assert term_data["terminal_reason"] == "operator_stop"
    assert not (run_root_dir / "sealed_exports").exists()


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

                if func_name in ["open"] and p.name not in [
                    "stage1_6b_canonical_source_storage.py"
                ]:
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and any(
                            m in str(arg.value) for m in ["w", "a", "x"]
                        ):
                            # Must not have raw open for writing outside storage primitives
                            pytest.fail(f"Unguarded raw file open in {p}: {ast.unparse(node)}")
