import dataclasses
import io
import json
import os
import socket
import urllib.request
from pathlib import Path
from typing import Any

import pytest

import src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage as storage_module
from configs import base
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_IDS as E_A_PROFILE_IDS,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer import (
    C5WorkItem,
    Stage16EBEventObserver,
    Stage16EBSemanticReducer,
    Stage16EBStructuralError,
    Stage16EBSupervisor,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_client import (
    ScheduledSlot,
    Stage16EBPublicClient,
    generate_event_slots,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    DelistingSemanticProjection,
    EventContract,
    EventProfileCore,
    MarketObservation,
    SourceConsumerCheckpoint,
    canonical_json,
    sha256_hex,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_storage import (
    RootWriterLock,
    Stage16EBStorageBlocked,
    validate_e_a_runtime_gate,
    validate_post_root_equality,
    verify_event_closed_tree_manifest,
    write_atomic_bytes,
    write_atomic_json,
)


class _MockResponse:
    def __init__(
        self,
        body: bytes,
        status: int = 200,
        headers: dict[str, str] | None = None,
    ):
        self._body = io.BytesIO(body)
        self.status = status
        self.code = status
        self.headers = headers or {}

    def read(self, amt: int | None = None) -> bytes:
        if amt is None:
            return self._body.read()
        return self._body.read(amt)

    def close(self) -> None:
        pass


class _MockOpener:
    def __init__(self, handler: Any):
        self._handler = handler
        self.calls: list[urllib.request.Request] = []

    def open(self, req: urllib.request.Request, timeout: float | None = None) -> Any:
        self.calls.append(req)
        return self._handler(req)


def _make_bapi_raw(article_id: str, body_text: str, data_code: str | None = None, title: str | None = None) -> bytes:
    code = data_code if data_code is not None else article_id
    title_str = title if title is not None else "Binance Will Delist REEFUSDT Perpetual Contract"
    body_tree = {
        "node": "root",
        "child": [
            {
                "node": "element",
                "tag": "p",
                "child": [{"node": "text", "text": body_text}],
            }
        ],
    }
    payload = {
        "code": "000000",
        "data": {
            "code": code,
            "title": title_str,
            "body": json.dumps(body_tree),
            "id": 12345,
            "publishDate": 1700000000000,
        },
    }
    return json.dumps(payload).encode("utf-8")



def test_reducer_valid_h2_eligible_projection(tmp_path: Path):
    article_id = "test_art_1"
    body_text = (
        "Binance Futures will close all positions and conduct automatic settlement on "
        "USDⓈ-M REEFUSDT Perpetual Contract at 2026-09-10 09:00 (UTC)."
    )
    raw_bytes = _make_bapi_raw(article_id, body_text)
    raw_sha = sha256_hex(raw_bytes)

    reducer = Stage16EBSemanticReducer()
    proj = reducer.reduce_detail_revision(
        supervisor_run_id="sup_1",
        source_root_realpath="/data/source",
        source_checkpoint_id="1" * 64,
        source_checkpoint_sha256="2" * 64,
        source_article_id=article_id,
        source_request_observation_id="req_1",
        source_detail_revision_id="rev_1",
        source_detail_raw_sha256=raw_sha,
        source_detail_raw_relative_path="raw/payload.bin",
        copied_source_raw_relative_path=f"source_detail_raw/{raw_sha}.bin",
        source_first_detected_at_ms=1000,
        source_detail_trusted_at_ms=2000,
        semantic_projected_at_ms=3000,
        raw_bytes=raw_bytes,
    )

    assert proj.eligibility_status == "eligible"
    assert proj.blocker is None
    assert proj.eligible_symbols_ordered == ["REEFUSDT"]
    assert proj.effective_delist_time_ms is not None
    assert proj.effective_delist_time_ms > 3000


def test_reducer_structural_data_code_mismatch_raises():
    article_id = "test_art_1"
    body_text = "Binance Futures delisting notice"
    raw_bytes = _make_bapi_raw(article_id, body_text, data_code="different_code_999")

    reducer = Stage16EBSemanticReducer()
    with pytest.raises(Stage16EBStructuralError, match="data_code_article_id_mismatch"):
        reducer.reduce_detail_revision(
            supervisor_run_id="sup_1",
            source_root_realpath="/data/source",
            source_checkpoint_id="1" * 64,
            source_checkpoint_sha256="2" * 64,
            source_article_id=article_id,
            source_request_observation_id="req_1",
            source_detail_revision_id="rev_1",
            source_detail_raw_sha256="3" * 64,
            source_detail_raw_relative_path="raw/payload.bin",
            copied_source_raw_relative_path="source_detail_raw/xxx.bin",
            source_first_detected_at_ms=1000,
            source_detail_trusted_at_ms=2000,
            semantic_projected_at_ms=3000,
            raw_bytes=raw_bytes,
        )


def test_reducer_semantic_blockers():
    article_id = "test_art_2"
    reducer = Stage16EBSemanticReducer()

    # 1. Zero eligible symbols
    body_no_symbols = "Binance Futures will close all positions and delist at 2026-09-10 09:00 (UTC)."
    raw_bytes1 = _make_bapi_raw(article_id, body_no_symbols, title="Binance System Update")


    proj1 = reducer.reduce_detail_revision(
        supervisor_run_id="sup_1",
        source_root_realpath="/data/source",
        source_checkpoint_id="1" * 64,
        source_checkpoint_sha256="2" * 64,
        source_article_id=article_id,
        source_request_observation_id="req_1",
        source_detail_revision_id="rev_1",
        source_detail_raw_sha256=sha256_hex(raw_bytes1),
        source_detail_raw_relative_path="raw/p.bin",
        copied_source_raw_relative_path="source_detail_raw/p.bin",
        source_first_detected_at_ms=1000,
        source_detail_trusted_at_ms=2000,
        semantic_projected_at_ms=3000,
        raw_bytes=raw_bytes1,
    )
    assert proj1.eligibility_status == "not_eligible"
    assert proj1.blocker == "zero_eligible_symbols"

    # 2. More than 3 symbols
    body_4_symbols = (
        "Binance Futures will close all positions and delist USDⓈ-M AAAAUSDT, BBBBUSDT, CCCCUSDT, and DDDDUSDT Perpetual Contracts "
        "at 2026-09-10 09:00 (UTC)."
    )
    raw_bytes2 = _make_bapi_raw(article_id, body_4_symbols)
    proj2 = reducer.reduce_detail_revision(
        supervisor_run_id="sup_1",
        source_root_realpath="/data/source",
        source_checkpoint_id="1" * 64,
        source_checkpoint_sha256="2" * 64,
        source_article_id=article_id,
        source_request_observation_id="req_1",
        source_detail_revision_id="rev_1",
        source_detail_raw_sha256=sha256_hex(raw_bytes2),
        source_detail_raw_relative_path="raw/p.bin",
        copied_source_raw_relative_path="source_detail_raw/p.bin",
        source_first_detected_at_ms=1000,
        source_detail_trusted_at_ms=2000,
        semantic_projected_at_ms=3000,
        raw_bytes=raw_bytes2,
    )
    assert proj2.eligibility_status == "not_eligible"
    assert proj2.blocker == "symbol_count_exceeds_three"

    # 3. Settlement time in past
    body_past_settle = (
        "Binance will close all positions and delist USDⓈ-M REEFUSDT Perpetual Contract "
        "at 2020-01-01 09:00 (UTC)."
    )
    raw_bytes3 = _make_bapi_raw(article_id, body_past_settle)
    proj3 = reducer.reduce_detail_revision(
        supervisor_run_id="sup_1",
        source_root_realpath="/data/source",
        source_checkpoint_id="1" * 64,
        source_checkpoint_sha256="2" * 64,
        source_article_id=article_id,
        source_request_observation_id="req_1",
        source_detail_revision_id="rev_1",
        source_detail_raw_sha256=sha256_hex(raw_bytes3),
        source_detail_raw_relative_path="raw/p.bin",
        copied_source_raw_relative_path="source_detail_raw/p.bin",
        source_first_detected_at_ms=1000,
        source_detail_trusted_at_ms=2000,
        semantic_projected_at_ms=1750000000000,
        raw_bytes=raw_bytes3,
    )
    assert proj3.eligibility_status == "not_eligible"
    assert proj3.blocker == "settlement_time_in_past"


def test_supervisor_admission_and_capacity_block(tmp_path: Path):
    sup_root = tmp_path / "sup_run_1"
    sup_root.mkdir()
    events_dir = tmp_path / "event_observations"
    events_dir.mkdir()

    # Pre-populate an active non-terminal event to test capacity block
    active_event_dir = events_dir / ("e" * 64)
    active_event_dir.mkdir()
    (active_event_dir / "event_contract.json").write_text('{"a":1}')

    supervisor = Stage16EBSupervisor(
        supervisor_root=sup_root,
        events_root=events_dir,
        e_a_root=tmp_path / "mock_ea",
    )

    # Test notice admission when active event exists -> capacity blocked
    adm = supervisor.evaluate_notice_admission(
        semantic_projection_id="a" * 64,
        source_article_id="123456",
        decided_at_ms=5000,
        active_event_id="e" * 64,
    )
    assert adm.decision == "event_observation_capacity_blocked"
    assert adm.blocker == "active_event_exists"


class MockOpenerAllSuccess:
    def __init__(self):
        self.calls = []

    def open(self, req, timeout=10.0):
        url = req.full_url
        self.calls.append(url)

        class Resp:
            def __init__(self, body):
                self.status = 200
                self.headers = {"Content-Type": "application/json"}
                self._body = body
                self._pos = 0

            def read(self, amt=None):
                if amt is None:
                    return self._body
                res = self._body[self._pos : self._pos + amt]
                self._pos += len(res)
                return res

            def close(self):
                pass

        if "depth" in url:
            body = b'{"lastUpdateId":100,"E":1700000000100,"T":1700000000000,"bids":[["60000.00","1.000"]],"asks":[["60010.00","1.000"]]}'
        elif "premiumIndex" in url:
            body = b'{"symbol":"BTCUSDT","markPrice":"60000.00","indexPrice":"59995.00","estimatedSettlePrice":"60000.00","lastFundingRate":"0.00010000","interestRate":"0.00010000","nextFundingTime":1700000000000,"time":1700000000000}'
        elif "fundingRate" in url:
            body = b'[{"symbol":"BTCUSDT","fundingRate":"0.00010000","fundingTime":1700000000000,"markPrice":"60000.00","rateType":"Regular"}]'
        elif "openInterestHist" in url:
            body = b'[{"symbol":"BTCUSDT","sumOpenInterest":"1000.000","sumOpenInterestValue":"60000000.00","timestamp":1700000000000}]'
        else:
            body = b'{}'
        return Resp(body)


def _build_canonical_ea_bundle(tmp_path: Path) -> tuple[Path, dict]:
    from scripts.external_signal_shadow.run_stage1_6e_a_market_data_capability_audit import (
        run_market_data_capability_audit,
    )

    proj = tmp_path / "mock_project"
    proj.mkdir(parents=True, exist_ok=True)
    audits_parent = proj / "data/external_signal_shadow/stage1_6e/capability_audits"
    audits_parent.mkdir(parents=True, exist_ok=True)
    shared_lock = proj / "data/external_signal_shadow/.stage1_5_storage_guard.lock"
    shared_lock.touch()

    step_a_proj = {
        "deployment_host_identity": "0" * 64,
        "hostname": "test-vps",
        "project_root_realpath": str(proj.resolve()),
        "capability_root_parent_filesystem_st_dev": os.stat(audits_parent).st_dev,
        "shared_lock_filesystem_st_dev": os.stat(shared_lock).st_dev,
        "network_namespace_inode": 12345,
        "proxy_environment": "absent",
        "runtime_user_uid": os.geteuid(),
        "deployment_git_commit": "a" * 40,
        "deployment_runtime_worktree_clean": True,
    }

    run_id = "stage1_6e_a_capability_20260903T073227Z_c431d5be400aabe216f15c6bf6bee48f"
    res = run_market_data_capability_audit(
        project_root=proj,
        capability_run_id=run_id,
        step_a_projection=step_a_proj,
        live_public_readonly=True,
        opener=MockOpenerAllSuccess(),
        skip_env_checks_for_test=True,
    )
    manifest_id = json.loads(
        (Path(res["output_root"]) / "manifest.json").read_text(encoding="utf-8")
    )["manifest_id"]
    storage_module._AUTHORIZED_E_A_MANIFEST_ID = manifest_id
    return Path(res["output_root"]), step_a_proj


def _create_event_root(
    *,
    supervisor: Stage16EBSupervisor,
    admission: Any,
    projection: DelistingSemanticProjection,
    step_a_projection: dict[str, Any],
    gate_info: dict[str, Any],
    deployment_git_commit: str,
    start_time_ms: int,
) -> Path:
    work_item = C5WorkItem(
        projection=projection,
        admission=admission,
        deterministic_event_root=supervisor.events_root / admission.event_id,
    )
    event_dir, lock = supervisor.create_event_root_dir(work_item)
    try:
        validate_post_root_equality(
            root=event_dir,
            lock_path=event_dir / ".stage1_6e_b_event_writer.lock",
            step_a_projection=step_a_projection,
            e_a_attestation=gate_info["environment_attestation"],
        )
        supervisor.populate_and_activate_event_root(
            c5_item=work_item,
            lock=lock,
            step_a_projection=step_a_projection,
            deployment_git_commit=deployment_git_commit,
            e_a_gate_info=gate_info,
            start_time_ms=start_time_ms,
        )
    except Exception:
        lock.release()
        raise
    return event_dir


def test_supervisor_initialize_event_root(tmp_path: Path):
    sup_root = tmp_path / "sup_run_2"
    sup_root.mkdir()
    events_dir = tmp_path / "event_observations"
    events_dir.mkdir()

    supervisor = Stage16EBSupervisor(
        supervisor_root=sup_root,
        events_root=events_dir,
        e_a_root=tmp_path / "mock_ea",
    )

    adm = supervisor.evaluate_notice_admission(
        semantic_projection_id="a" * 64,
        source_article_id="123456",
        decided_at_ms=5000,
        active_event_id=None,
    )
    assert adm.decision == "admitted"

    proj = DelistingSemanticProjection.create(
        supervisor_run_id="sup_2",
        source_root_realpath="/data/source",
        source_checkpoint_id="1" * 64,
        source_checkpoint_sha256="2" * 64,
        source_article_id="123456",
        source_request_observation_id="req_1",
        source_detail_revision_id="rev_1",
        source_detail_raw_sha256="3" * 64,
        source_detail_raw_relative_path="raw/p.bin",
        copied_source_raw_relative_path="source_detail_raw/p.bin",
        g2_body_normalization_version="stage1_6a_bapi_body_tree_v2",
        g2_semantic_extractor_version="stage1_6a_extractor_v2",
        normalized_body_sha256="4" * 64,
        source_first_detected_at_ms=1000,
        source_detail_trusted_at_ms=2000,
        eligible_symbols_ordered=["REEFUSDT"],
        effective_delist_time_ms=6000000,
        eligibility_status="eligible",
        blocker=None,
        semantic_projected_at_ms=3000,
    )

    ea_root, step_a_proj = _build_canonical_ea_bundle(tmp_path)
    gate_info = validate_e_a_runtime_gate(ea_root, step_a_projection=step_a_proj)
    event_dir = _create_event_root(
        supervisor=supervisor,
        admission=adm,
        projection=proj,
        step_a_projection=step_a_proj,
        deployment_git_commit="a" * 40,
        gate_info=gate_info,
        start_time_ms=5000,
    )

    assert event_dir.is_dir()
    assert (event_dir / ".stage1_6e_b_event_writer.lock").exists()
    assert (event_dir / "execution_environment_attestation.json").is_file()
    att_eb = json.loads((event_dir / "execution_environment_attestation.json").read_text(encoding="utf-8"))
    assert att_eb["deployment_git_commit"] == "a" * 40
    assert (event_dir / "environment_authority_receipt.json").exists()
    assert (event_dir / "event_contract.json").exists()
    assert (event_dir / "event_checkpoint.json").exists()
    for base_pid in E_A_PROFILE_IDS:
        p_path = event_dir / "profile_attestations" / f"REEFUSDT.{base_pid}.json"
        assert p_path.exists()
        derived_profile = json.loads(p_path.read_text(encoding="utf-8"))
        assert (
            derived_profile["base_e_a_profile_attestation_sha256"]
            == gate_info["profile_attestation_sha256_by_id"][base_pid]
        )
        assert (
            derived_profile["http_profile_core"]["max_raw_response_bytes"]
            == derived_profile["event_max_raw_response_bytes"]
        )
        profile_copy = dict(derived_profile)
        saved_attest = profile_copy.pop("profile_attestation_sha256")
        assert saved_attest == sha256_hex(canonical_json(profile_copy))


def _setup_event_dir(tmp_path: Path, symbols: list[str] | None = None) -> Path:
    if symbols is None:
        symbols = ["REEFUSDT"]
    ea_root, step_a_proj = _build_canonical_ea_bundle(tmp_path)
    gate_info = validate_e_a_runtime_gate(ea_root, step_a_projection=step_a_proj)
    sup_root = tmp_path / "supervisor"
    sup_root.mkdir(parents=True, exist_ok=True)
    events_dir = tmp_path / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    supervisor = Stage16EBSupervisor(
        supervisor_root=sup_root,
        events_root=events_dir,
        e_a_root=ea_root,
    )
    adm = supervisor.evaluate_notice_admission(
        semantic_projection_id="a" * 64,
        source_article_id="123456",
        decided_at_ms=1700000000000,
        active_event_id=None,
    )
    proj = DelistingSemanticProjection.create(
        supervisor_run_id="sup_1",
        source_root_realpath="/data/source",
        source_checkpoint_id="1" * 64,
        source_checkpoint_sha256="2" * 64,
        source_article_id="123456",
        source_request_observation_id="req_1",
        source_detail_revision_id="rev_1",
        source_detail_raw_sha256="3" * 64,
        source_detail_raw_relative_path="raw/p.bin",
        copied_source_raw_relative_path="source_detail_raw/p.bin",
        g2_body_normalization_version="stage1_6a_bapi_body_tree_v2",
        g2_semantic_extractor_version="stage1_6a_extractor_v2",
        normalized_body_sha256="4" * 64,
        source_first_detected_at_ms=1000,
        source_detail_trusted_at_ms=2000,
        eligible_symbols_ordered=symbols,
        effective_delist_time_ms=1700000000000 + 86400000,
        eligibility_status="eligible",
        blocker=None,
        semantic_projected_at_ms=1700000000000,
    )
    event_dir = _create_event_root(
        supervisor=supervisor,
        admission=adm,
        projection=proj,
        step_a_projection=step_a_proj,
        deployment_git_commit="a" * 40,
        gate_info=gate_info,
        start_time_ms=1700000000000,
    )
    return event_dir


def test_event_observer_step_slot_deadline_missed(tmp_path: Path):
    event_dir = _setup_event_dir(tmp_path)
    opener = _MockOpener(lambda req: _MockResponse(b"{}"))
    client = Stage16EBPublicClient(opener=opener)
    obs_runner = Stage16EBEventObserver(event_dir, client)
    obs_runner.resume_and_validate()

    slot = obs_runner.slots[0]
    current_time = slot.due_at_ms + base.EXTERNAL_SIGNAL_STAGE1_6E_B_SLOT_DEADLINE_MS + 1
    observation = obs_runner.step_slot(slot, current_time)

    assert observation.outcome_kind == "slot_missed_deadline"
    assert observation.raw_payload_persisted is False
    assert len(opener.calls) == 0
    assert obs_runner.checkpoint.inflight_slot_intent is None
    assert slot.slot_id in obs_runner.checkpoint.completed_slot_ids_ordered
    obs_runner.close()


def test_event_observer_step_slot_verified(tmp_path: Path):
    event_dir = _setup_event_dir(tmp_path)
    payload = {
        "lastUpdateId": 123456,
        "E": 1700000001000,
        "T": 1700000000500,
        "bids": [["100.0", "1.0"]],
        "asks": [["101.0", "2.0"]],
    }
    raw = json.dumps(payload).encode("utf-8")
    opener = _MockOpener(lambda req: _MockResponse(raw, status=200, headers={"Content-Type": "application/json"}))
    client = Stage16EBPublicClient(opener=opener)

    obs_runner = Stage16EBEventObserver(event_dir, client)
    obs_runner.resume_and_validate()

    slot = obs_runner.slots[0]
    current_time = slot.due_at_ms + 1000
    obs = obs_runner.step_slot(slot, current_time)

    assert obs.outcome_kind == "response_verified"
    assert obs.schema_validation_status == "verified"
    assert obs.time_validation_status == "verified"
    assert obs.raw_payload_persisted is True
    assert obs.raw_sha256 == sha256_hex(raw)
    assert obs.raw_relative_path is not None
    raw_path = event_dir / obs.raw_relative_path
    assert raw_path.is_file()
    assert raw_path.read_bytes() == raw
    assert obs_runner.checkpoint.inflight_slot_intent is None
    assert slot.slot_id in obs_runner.checkpoint.completed_slot_ids_ordered
    obs_runner.close()


def test_event_observer_step_slot_http_error(tmp_path: Path):
    event_dir = _setup_event_dir(tmp_path)

    def timeout_handler(req: urllib.request.Request):
        raise socket.timeout("timed out")

    opener = _MockOpener(timeout_handler)
    client = Stage16EBPublicClient(opener=opener)

    obs_runner = Stage16EBEventObserver(event_dir, client)
    obs_runner.resume_and_validate()

    slot = obs_runner.slots[0]
    current_time = slot.due_at_ms + 1000
    obs = obs_runner.step_slot(slot, current_time)

    assert obs.outcome_kind == "request_timeout"
    assert obs.raw_payload_persisted is False
    assert obs.raw_sha256 is None
    assert obs_runner.checkpoint.inflight_slot_intent is None
    assert slot.slot_id in obs_runner.checkpoint.completed_slot_ids_ordered
    obs_runner.close()


def test_event_observer_uses_profile_raw_response_cap(tmp_path: Path):
    event_dir = _setup_event_dir(tmp_path)
    opener = _MockOpener(lambda req: _MockResponse(b"x" * 32769))
    obs_runner = Stage16EBEventObserver(event_dir, Stage16EBPublicClient(opener=opener))
    obs_runner.resume_and_validate()

    slot = next(
        item
        for item in obs_runner.slots
        if item.base_e_a_profile_id == "binance_usdm_rest_premium_index_v1"
    )
    observation = obs_runner.step_slot(slot, slot.due_at_ms + 1)

    assert observation.outcome_kind == "raw_size_exceeded"
    assert observation.raw_payload_persisted is False
    obs_runner.close()


def test_event_observer_terminal_and_manifest(tmp_path: Path):
    event_dir = _setup_event_dir(tmp_path)
    payload = {
        "lastUpdateId": 123456,
        "E": 1700000001000,
        "T": 1700000000500,
        "bids": [["100.0", "1.0"]],
        "asks": [["101.0", "2.0"]],
    }
    raw = json.dumps(payload).encode("utf-8")
    opener = _MockOpener(lambda req: _MockResponse(raw, status=200, headers={"Content-Type": "application/json"}))
    client = Stage16EBPublicClient(opener=opener)

    obs_runner = Stage16EBEventObserver(event_dir, client)
    obs_runner.resume_and_validate()

    # Step two slots: one verified, one missed
    slot0 = obs_runner.slots[0]
    obs0 = obs_runner.step_slot(slot0, slot0.due_at_ms + 100)
    assert obs0.outcome_kind == "response_verified"

    slot1 = obs_runner.slots[1]
    obs1 = obs_runner.step_slot(slot1, slot1.due_at_ms + base.EXTERNAL_SIGNAL_STAGE1_6E_B_SLOT_DEADLINE_MS + 1)
    assert obs1.outcome_kind == "slot_missed_deadline"

    # Set expected_slot_count to 2 so finalize_terminal succeeds
    obs_runner.contract = dataclasses.replace(obs_runner.contract, expected_slot_count=2)
    new_contract_sha = write_atomic_json(event_dir / "event_contract.json", obs_runner.contract.to_dict())
    obs_runner.checkpoint = dataclasses.replace(obs_runner.checkpoint, event_contract_sha256=new_contract_sha)
    write_atomic_json(event_dir / "event_checkpoint.json", obs_runner.checkpoint.to_dict())

    term = obs_runner.finalize_terminal(current_time_ms=1700000100000)
    assert term.status == "complete"
    assert term.coverage_status == "incomplete"
    assert term.successful_slot_count == 1
    assert term.missed_slot_count == 1
    assert term.durable_slot_count == 2
    assert (event_dir / "terminal_status.json").exists()
    assert (event_dir / "manifest.json").exists()

    verify_event_closed_tree_manifest(event_dir)
    obs_runner.close()


def _get_first_slot(event_dir: Path) -> ScheduledSlot:
    contract_dict = json.loads((event_dir / "event_contract.json").read_text(encoding="utf-8"))
    contract = EventContract(**contract_dict)
    profile_dir = event_dir / "profile_attestations"
    profile_cores = {}
    for sym in contract.canonical_symbols_ordered:
        for pid in E_A_PROFILE_IDS:
            p_dict = json.loads((profile_dir / f"{sym}.{pid}.json").read_text(encoding="utf-8"))
            profile_cores[f"{sym}:{pid}"] = EventProfileCore(**p_dict)
    slots = generate_event_slots(contract, profile_cores)
    return slots[0]


def test_event_observer_wal_reconcile_prepared_intent(tmp_path: Path):
    event_dir = _setup_event_dir(tmp_path)
    chk_path = event_dir / "event_checkpoint.json"
    chk_dict = json.loads(chk_path.read_text(encoding="utf-8"))
    first_slot = _get_first_slot(event_dir)

    intent = {
        "slot_id": first_slot.slot_id,
        "request_identity": first_slot.request_identity,
        "request_sequence": 1,
        "base_e_a_profile_id": first_slot.base_e_a_profile_id,
        "canonical_symbol": first_slot.canonical_symbol,
        "due_at_ms": first_slot.due_at_ms,
        "reserved_at_ms": first_slot.due_at_ms + 1000,
        "stage": "prepared",
        "raw_sha256": None,
        "raw_relative_path": None,
        "raw_byte_count": None,
    }
    chk_dict["inflight_slot_intent"] = intent
    chk_path.write_text(json.dumps(chk_dict), encoding="utf-8")

    client = Stage16EBPublicClient(opener=_MockOpener(lambda req: _MockResponse(b"{}")))
    obs_runner = Stage16EBEventObserver(event_dir, client)
    obs_runner.resume_and_validate()

    assert obs_runner.checkpoint.inflight_slot_intent is None
    assert len(obs_runner.observations) == 1
    obs = obs_runner.observations[0]
    assert obs.outcome_kind == "request_outcome_unknown_after_restart"
    assert obs.raw_payload_persisted is False
    assert first_slot.slot_id in obs_runner.checkpoint.completed_slot_ids_ordered
    obs_runner.close()


def test_event_observer_wal_reconcile_raw_persisted_intent(tmp_path: Path):
    event_dir = _setup_event_dir(tmp_path)
    chk_path = event_dir / "event_checkpoint.json"
    chk_dict = json.loads(chk_path.read_text(encoding="utf-8"))
    first_slot = _get_first_slot(event_dir)

    raw_bytes = b'{"lastUpdateId": 123456}'
    raw_sha = sha256_hex(raw_bytes)
    raw_rel = f"raw/{raw_sha}.body"
    write_atomic_bytes(event_dir / raw_rel, raw_bytes)

    intent = {
        "slot_id": first_slot.slot_id,
        "request_identity": first_slot.request_identity,
        "request_sequence": 1,
        "base_e_a_profile_id": first_slot.base_e_a_profile_id,
        "canonical_symbol": first_slot.canonical_symbol,
        "due_at_ms": first_slot.due_at_ms,
        "reserved_at_ms": first_slot.due_at_ms + 1000,
        "stage": "raw_persisted",
        "raw_sha256": raw_sha,
        "raw_relative_path": raw_rel,
        "raw_byte_count": len(raw_bytes),
    }
    chk_dict["inflight_slot_intent"] = intent
    chk_path.write_text(json.dumps(chk_dict), encoding="utf-8")

    client = Stage16EBPublicClient(opener=_MockOpener(lambda req: _MockResponse(b"{}")))
    obs_runner = Stage16EBEventObserver(event_dir, client)
    obs_runner.resume_and_validate()

    assert obs_runner.checkpoint.inflight_slot_intent is None
    assert len(obs_runner.observations) == 1
    obs = obs_runner.observations[0]
    assert obs.outcome_kind == "request_outcome_unknown_after_restart"
    assert obs.raw_payload_persisted is True
    assert obs.raw_sha256 == raw_sha
    assert obs.raw_relative_path == raw_rel
    assert first_slot.slot_id in obs_runner.checkpoint.completed_slot_ids_ordered
    obs_runner.close()


def test_event_observer_wal_reconcile_corrupt_raw(tmp_path: Path):
    event_dir = _setup_event_dir(tmp_path)
    chk_path = event_dir / "event_checkpoint.json"
    chk_dict = json.loads(chk_path.read_text(encoding="utf-8"))
    first_slot = _get_first_slot(event_dir)

    raw_rel = "raw/corrupt.body"
    write_atomic_bytes(event_dir / raw_rel, b"CORRUPT_BYTES")

    intent = {
        "slot_id": first_slot.slot_id,
        "request_identity": first_slot.request_identity,
        "request_sequence": 1,
        "base_e_a_profile_id": first_slot.base_e_a_profile_id,
        "canonical_symbol": first_slot.canonical_symbol,
        "due_at_ms": first_slot.due_at_ms,
        "reserved_at_ms": first_slot.due_at_ms + 1000,
        "stage": "raw_persisted",
        "raw_sha256": "0" * 64,  # Mismatched hash
        "raw_relative_path": raw_rel,
        "raw_byte_count": 13,
    }
    chk_dict["inflight_slot_intent"] = intent
    chk_path.write_text(json.dumps(chk_dict), encoding="utf-8")

    client = Stage16EBPublicClient(opener=_MockOpener(lambda req: _MockResponse(b"{}")))
    obs_runner = Stage16EBEventObserver(event_dir, client)
    with pytest.raises(Stage16EBStorageBlocked, match="local_integrity_failed"):
        obs_runner.resume_and_validate()

    assert (event_dir / "terminal_status.json").exists()
    assert not (event_dir / "manifest.json").exists()
    term = json.loads((event_dir / "terminal_status.json").read_text(encoding="utf-8"))
    assert term["status"] == "failed"
    assert term["terminal_reason"] == "local_integrity_failed"
    obs_runner.close()


def test_event_observer_wal_reconcile_obs_one_ahead(tmp_path: Path):
    event_dir = _setup_event_dir(tmp_path)
    obs_file = event_dir / "observations.jsonl"
    contract_dict = json.loads((event_dir / "event_contract.json").read_text(encoding="utf-8"))
    first_slot = _get_first_slot(event_dir)
    profile_attest_sha = contract_dict["e_a_profile_attestation_sha256_by_id"][first_slot.base_e_a_profile_id]

    obs = MarketObservation.create_missed_deadline(
        event_id=contract_dict["event_id"],
        slot_id=first_slot.slot_id,
        slot_family=first_slot.slot_family,
        slot_index=first_slot.slot_index,
        due_at_ms=first_slot.due_at_ms,
        completed_at_ms=first_slot.due_at_ms + base.EXTERNAL_SIGNAL_STAGE1_6E_B_SLOT_DEADLINE_MS + 1,
        canonical_symbol=first_slot.canonical_symbol,
        base_e_a_profile_id=first_slot.base_e_a_profile_id,
        profile_attestation_sha256=profile_attest_sha,
        request_identity=first_slot.request_identity,
    )
    obs_file.write_text(json.dumps(obs.to_dict()) + "\n", encoding="utf-8")
    expected_obs_sha = sha256_hex(canonical_json(obs.to_dict()).encode("utf-8"))

    client = Stage16EBPublicClient(opener=_MockOpener(lambda req: _MockResponse(b"{}")))
    obs_runner = Stage16EBEventObserver(event_dir, client)
    obs_runner.resume_and_validate()

    assert obs_runner.checkpoint.completed_slot_ids_ordered == [first_slot.slot_id]
    assert obs_runner.checkpoint.last_observation_sha256 == expected_obs_sha
    obs_runner.close()


def test_fresh_bootstrap_writes_checkpoint_only_no_historical_replay(tmp_path: Path):
    from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_source import (
        Stage16EBSourceConsumer,
    )
    from tests.research.external_signal_shadow.test_stage1_6e_b_live_semantic_observer_source import (
        _setup_canonical_1_6d_source,
    )

    source_dir = tmp_path / "source_bootstrap"
    run_id = "run_boot_1"
    now_ms = 1_725_500_000_000
    chk_dict, rev_rec, obs_rec, _ = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms
    )

    sup_root = tmp_path / "supervisor_boot"
    events_root = tmp_path / "events_boot"
    ea_root = tmp_path / "ea_boot"
    sup = Stage16EBSupervisor(
        supervisor_root=sup_root,
        events_root=events_root,
        e_a_root=ea_root,
    )

    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=sup_root / "source_consumer_checkpoint.json",
    )

    projs = sup.step_source_stream(consumer, current_time_ms=now_ms)
    assert projs is None

    # Verify consumer checkpoint was created atomically at current boundary
    chk_file = sup_root / "source_consumer_checkpoint.json"
    assert chk_file.is_file()
    saved_chk = json.loads(chk_file.read_text(encoding="utf-8"))
    assert saved_chk["detail_revisions_committed_offset"] == chk_dict["stream_offsets"]["detail_revisions.jsonl"]
    assert saved_chk["detail_revisions_last_line_sha256"] == chk_dict["stream_last_hashes"]["detail_revisions.jsonl"]
    assert saved_chk["last_consumed_detail_revision_record_seq"] == rev_rec.record_seq

    # Zero historical raw copying, zero projections, zero admissions, zero event roots!
    assert not (sup_root / "semantic_projections.jsonl").exists()
    assert not (sup_root / "event_admissions.jsonl").exists()
    assert not (sup_root / "source_detail_raw").exists() or list((sup_root / "source_detail_raw").iterdir()) == []
    assert not events_root.exists() or list(events_root.iterdir()) == []


def test_suffix_consumption_processes_new_revisions(tmp_path: Path):
    from datetime import datetime, timezone

    from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
        DETAIL_REQUEST_VARIANT,
        DETAIL_SOURCE_LOCALE,
        DETAIL_SOURCE_SURFACE,
        SOURCE_PROFILE_ID,
        CaptureMode,
        DetailObservationRecord,
        DetailRevisionRecord,
        compute_detail_revision_id,
        compute_live_v3_checkpoint_id,
    )
    from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_source import (
        Stage16EBSourceConsumer,
    )
    from tests.research.external_signal_shadow.test_stage1_6e_b_live_semantic_observer_source import (
        _setup_canonical_1_6d_source,
    )

    source_dir = tmp_path / "source_suffix"
    run_id = "run_suffix_1"
    now_ms = 1_725_500_000_000
    chk_dict, rev_rec, obs_rec, _ = _setup_canonical_1_6d_source(
        source_dir, run_id, captured_at_ms=now_ms, heartbeat_at_ms=now_ms, article_id="10001"
    )

    sup_root = tmp_path / "supervisor_suffix"
    events_root = tmp_path / "events_suffix"
    ea_root = tmp_path / "ea_suffix"
    sup = Stage16EBSupervisor(
        supervisor_root=sup_root,
        events_root=events_root,
        e_a_root=ea_root,
    )
    consumer = Stage16EBSourceConsumer(
        authorized_source_root=source_dir,
        authorized_run_id=run_id,
        consumer_checkpoint_path=sup_root / "source_consumer_checkpoint.json",
    )

    # 1. Fresh bootstrap
    projs_boot = sup.step_source_stream(consumer, current_time_ms=now_ms)
    assert projs_boot is None

    # 2. Append new revision and observation for article 10002
    step2_ms = now_ms + 60_000
    article_2 = "10002"
    payload_2 = (
        b'{"code":"000000","data":{"id":10002,"title":"Binance Will Delist A, B on 2026-09-10","body":"Delist A, B"}}'
    )
    raw2_sha = sha256_hex(payload_2)
    raw2_rel = f"raw_payloads/detail/{article_2}/{raw2_sha}.bin"
    raw2_p = source_dir / raw2_rel
    raw2_p.parent.mkdir(parents=True, exist_ok=True)
    raw2_p.write_bytes(payload_2)

    date2_str = datetime.fromtimestamp(step2_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
    obs2_rel = f"detail_observations/{date2_str}.jsonl"
    obs2_p = source_dir / obs2_rel

    probe_sha = chk_dict["source_profile_attestation_sha256"]
    obs2_rec = DetailObservationRecord(
        schema_version="stage1_6b_detail_observation_v1",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        request_headers_profile_sha256=probe_sha,
        run_id=run_id,
        poll_seq=2,
        record_seq=2,
        request_observation_id=f"req_obs_{article_2}_001",
        source_article_id=article_2,
        request_variant=DETAIL_REQUEST_VARIANT,
        requested_url=f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail?articleId={article_2}",
        final_url=f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail?articleId={article_2}",
        http_status=200,
        content_type="application/json",
        raw_payload_sha256=raw2_sha,
        raw_payload_bytes=len(payload_2),
        raw_payload_relative_path=raw2_rel,
        trust_validation_status="trusted",
        t_detail_receive_ms=step2_ms,
        captured_at_ms=step2_ms,
    )
    obs2_line = canonical_json(obs2_rec.to_dict()) + "\n"
    with obs2_p.open("a", encoding="utf-8") as f:
        f.write(obs2_line)
    obs2_offset = obs2_p.stat().st_size
    obs2_last_hash = sha256_hex(obs2_line.strip().encode("utf-8"))

    rev2_id = compute_detail_revision_id(
        source_article_id=article_2,
        source_surface=DETAIL_SOURCE_SURFACE,
        source_locale=DETAIL_SOURCE_LOCALE,
        request_variant=DETAIL_REQUEST_VARIANT,
        detail_raw_sha256=raw2_sha,
    )
    rev2_rec = DetailRevisionRecord(
        schema_version="stage1_6b_detail_revision_v1",
        capture_mode=CaptureMode.LIVE_OBSERVED.value,
        source_profile_id=SOURCE_PROFILE_ID,
        source_article_id=article_2,
        source_surface=DETAIL_SOURCE_SURFACE,
        source_locale=DETAIL_SOURCE_LOCALE,
        request_variant=DETAIL_REQUEST_VARIANT,
        detail_revision_id=rev2_id,
        detail_raw_sha256=raw2_sha,
        raw_payload_relative_path=raw2_rel,
        t_detail_trusted_ms=step2_ms,
        t_raw_persisted_ms=step2_ms,
        captured_at_ms=step2_ms,
        record_seq=2,
    )
    rev_p = source_dir / "detail_revisions.jsonl"
    rev2_line = canonical_json(rev2_rec.to_dict()) + "\n"
    with rev_p.open("a", encoding="utf-8") as f:
        f.write(rev2_line)
    rev2_offset = rev_p.stat().st_size
    rev2_last_hash = sha256_hex(rev2_line.strip().encode("utf-8"))

    chk_dict["poll_seq"] = 2
    chk_dict["record_seq"] = 2
    chk_dict["heartbeat_at_ms"] = step2_ms
    chk_dict["stream_offsets"]["detail_revisions.jsonl"] = rev2_offset
    chk_dict["stream_last_hashes"]["detail_revisions.jsonl"] = rev2_last_hash
    chk_dict["stream_offsets"][obs2_rel] = obs2_offset
    chk_dict["stream_last_hashes"][obs2_rel] = obs2_last_hash
    chk_dict["checkpoint_id"] = compute_live_v3_checkpoint_id(chk_dict)
    (source_dir / "observer_checkpoint.json").write_text(canonical_json(chk_dict), encoding="utf-8")

    # 3. Consume suffix
    c5_item = sup.step_source_stream(consumer, current_time_ms=step2_ms)
    assert c5_item is not None
    p = c5_item.projection
    assert p.source_article_id == article_2
    assert p.source_request_observation_id == obs2_rec.request_observation_id
    assert p.source_detail_revision_id == rev2_id
    assert p.source_detail_raw_sha256 == raw2_sha
    assert p.source_detail_raw_relative_path == raw2_rel

    # Suffix persistence verified
    raw_dest = sup_root / "source_detail_raw" / f"{raw2_sha}.bin"
    assert raw_dest.is_file()
    assert raw_dest.read_bytes() == payload_2

    # Step-source-stream produces projections/admissions but does NOT create an event root
    assert not events_root.exists() or list(events_root.iterdir()) == []


def test_supervisor_try_release_terminal_capacity_c8_c9_and_failed_writer(tmp_path: Path):
    ea_root, step_a_proj = _build_canonical_ea_bundle(tmp_path)
    sup_root = tmp_path / "supervisor_term"
    events_dir = tmp_path / "events_term"
    sup = Stage16EBSupervisor(
        supervisor_root=sup_root,
        events_root=events_dir,
        e_a_root=ea_root,
    )
    event_id = "e" * 64
    chk = SourceConsumerCheckpoint.create(
        supervisor_run_id="sup_1",
        source_root_realpath="/data/source",
        source_checkpoint_id="1" * 64,
        source_checkpoint_sha256="2" * 64,
        source_stream_offsets={"detail_revisions.jsonl": 0},
        source_stream_last_hashes={"detail_revisions.jsonl": None},
        detail_revisions_committed_offset=0,
        detail_revisions_last_line_sha256=None,
        last_consumed_detail_revision_record_seq=None,
        active_notice_event_key="b" * 64,
        active_event_id=event_id,
        updated_at_ms=1700000000000,
    )
    sup_root.mkdir(parents=True, exist_ok=True)
    events_dir.mkdir(parents=True, exist_ok=True)
    write_atomic_json(sup_root / "source_consumer_checkpoint.json", chk.to_dict())

    event_dir = events_dir / event_id
    event_dir.mkdir()
    lock_file = event_dir / ".stage1_6e_b_event_writer.lock"
    lock_file.touch()

    # 1. C8: terminal_status.json does not exist -> returns False, retains capacity
    assert not sup.try_release_terminal_capacity(1700000001000)
    assert sup.get_active_event_id() == event_id

    # 2. C8: terminal_status.json exists but malformed/wrong schema -> returns False, retains capacity
    write_atomic_json(event_dir / "terminal_status.json", {"schema_version": "bad", "status": "failed"})
    assert not sup.try_release_terminal_capacity(1700000002000)
    assert sup.get_active_event_id() == event_id

    # 3. C9: terminal_status.json status="complete", manifest missing -> returns False, retains capacity
    write_atomic_json(event_dir / "terminal_status.json", {"schema_version": "stage1_6e_b_terminal_status_v1", "status": "complete"})
    assert not sup.try_release_terminal_capacity(1700000003000)
    assert sup.get_active_event_id() == event_id

    # 4. C9: manifest exists but invalid/corrupt -> returns False, retains capacity
    write_atomic_json(event_dir / "manifest.json", {"manifest_id": "corrupt"})
    assert not sup.try_release_terminal_capacity(1700000004000)
    assert sup.get_active_event_id() == event_id
    (event_dir / "manifest.json").unlink()

    # 5. Failed terminal with writer lock held -> returns False, retains capacity
    write_atomic_json(event_dir / "terminal_status.json", {"schema_version": "stage1_6e_b_terminal_status_v1", "status": "failed"})
    with RootWriterLock(event_dir, ".stage1_6e_b_event_writer.lock"):
        assert not sup.try_release_terminal_capacity(1700000005000)
        assert sup.get_active_event_id() == event_id

    # 6. Failed terminal with lock file missing -> returns False, retains capacity
    lock_file.unlink()
    assert not sup.try_release_terminal_capacity(1700000006000)
    assert sup.get_active_event_id() == event_id

    # 7. Failed terminal with symlink lock -> returns False, retains capacity
    real_f = tmp_path / "other_file"
    real_f.touch()
    lock_file.symlink_to(real_f)
    assert not sup.try_release_terminal_capacity(1700000007000)
    assert sup.get_active_event_id() == event_id
    lock_file.unlink()

    # 8. Failed terminal with nonzero lock -> returns False, retains capacity
    lock_file.write_bytes(b"nonzero")
    assert not sup.try_release_terminal_capacity(1700000008000)
    assert sup.get_active_event_id() == event_id
    lock_file.unlink()

    # 9. Failed terminal with manifest present -> returns False, retains capacity
    lock_file.touch()
    (event_dir / "manifest.json").touch()
    assert not sup.try_release_terminal_capacity(1700000009000)
    assert sup.get_active_event_id() == event_id
    (event_dir / "manifest.json").unlink()

    # 10. Valid failed terminal with stopped writer (unheld, 0-byte regular, no manifest) -> returns True, releases capacity!
    assert sup.try_release_terminal_capacity(1700000010000)
    assert sup.get_active_event_id() is None
    cur_chk = json.loads((sup_root / "source_consumer_checkpoint.json").read_text(encoding="utf-8"))
    assert cur_chk["active_event_id"] is None
    assert cur_chk["active_notice_event_key"] is None

