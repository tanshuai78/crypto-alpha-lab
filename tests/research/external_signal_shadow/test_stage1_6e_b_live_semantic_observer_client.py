"""Tests for Stage 1.6E-B slot scheduler, deadline enforcement, and public HTTP client."""

from __future__ import annotations

import io
import json
import socket
import urllib.error
import urllib.request
from typing import Any

import pytest

from configs import base
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_CORES as E_A_PROFILE_CORES,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_IDS as E_A_PROFILE_IDS,
)
from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    compute_profile_attestation_sha256,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_client import (
    Stage16EBPublicClient,
    generate_event_slots,
    validate_event_response_schema,
    validate_event_response_time,
)
from src.research.external_signal_shadow.stage1_6e_b_live_semantic_observer_models import (
    EventContract,
    derive_event_profile_core,
    stage1_6e_b_permissions,
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
        self.headers = headers or {"Content-Type": "application/json"}

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


def _make_dummy_contract(symbols: list[str]) -> tuple[EventContract, dict[str, Any]]:
    event_id = "a" * 64
    start_ms = 1_700_000_000_000
    e_a_manifest_id = "e" * 64
    profile_cores = {}
    for sym in symbols:
        for pid in E_A_PROFILE_IDS:
            base_core = E_A_PROFILE_CORES[pid]
            core = derive_event_profile_core(
                event_id=event_id,
                source_article_id="art1",
                source_detail_revision_id="rev1",
                canonical_symbol=sym,
                base_e_a_manifest_id=e_a_manifest_id,
                base_e_a_profile_id=pid,
                base_e_a_profile_attestation_sha256=compute_profile_attestation_sha256(base_core),
                base_e_a_profile_core=base_core,
            )
            profile_cores[f"{sym}:{pid}"] = core

    contract = EventContract(
        schema_version="stage1_6e_b_event_contract_v1",
        event_id=event_id,
        supervisor_run_id="run1",
        semantic_projection_id="proj1",
        semantic_projection_row_sha256="1" * 64,
        admission_id="adm1",
        admission_row_sha256="2" * 64,
        source_article_id="art1",
        source_detail_revision_id="rev1",
        source_detail_raw_sha256="3" * 64,
        source_checkpoint_id="chk1",
        source_checkpoint_sha256="4" * 64,
        effective_delist_time_ms=start_ms + 86_400_000,
        event_window_started_at_ms=start_ms,
        event_window_ends_at_ms=start_ms + base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_WINDOW_MS,
        window_duration_ms=base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_WINDOW_MS,
        canonical_symbols_ordered=symbols,
        canonical_symbols_normalized=symbols,
        symbol_set_sha256="5" * 64,
        expected_slot_count=len(symbols) * 1586,
        e_a_manifest_id=e_a_manifest_id,
        e_a_manifest_sha256="6" * 64,
        e_a_profile_attestation_sha256_by_id={pid: "7" * 64 for pid in E_A_PROFILE_IDS},
        execution_environment_attestation_sha256="8" * 64,
        storage_contract={
            "event_root_max_bytes": base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ROOT_MAX_BYTES,
            "event_ordinary_reserve_bytes": base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ORDINARY_RESERVE_BYTES,
            "event_emergency_reserve_bytes": base.EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_EMERGENCY_RESERVE_BYTES,
        },
        permissions=stage1_6e_b_permissions(),
    )
    return contract, profile_cores


def test_slot_schedule_generation():
    contract_1, cores_1 = _make_dummy_contract(["REEFUSDT"])
    slots_1 = generate_event_slots(contract_1, cores_1)
    assert len(slots_1) == 1586

    # Verify counts per family
    depth_slots = [s for s in slots_1 if s.slot_family == "depth_60s"]
    premium_slots = [s for s in slots_1 if s.slot_family == "premium_60s"]
    oi_slots = [s for s in slots_1 if s.slot_family == "oi_5m"]
    f_start = [s for s in slots_1 if s.slot_family == "funding_start"]
    f_end = [s for s in slots_1 if s.slot_family == "funding_end"]

    assert len(depth_slots) == 720
    assert len(premium_slots) == 720
    assert len(oi_slots) == 144
    assert len(f_start) == 1
    assert len(f_end) == 1

    # Verify multi-symbol count
    contract_3, cores_3 = _make_dummy_contract(["REEFUSDT", "BTCUSDT", "ETHUSDT"])
    slots_3 = generate_event_slots(contract_3, cores_3)
    assert len(slots_3) == 3 * 1586

    # Verify dispatch order at start time:
    # At start time: depth -> premium -> funding -> oi -> then symbol lexical
    start_slots = [s for s in slots_3 if s.due_at_ms == contract_3.event_window_started_at_ms]
    # Expect: 3 depth, then 3 premium, then 3 funding_start, then 3 oi
    families = [s.slot_family for s in start_slots]
    assert families[:3] == ["depth_60s", "depth_60s", "depth_60s"]
    assert families[3:6] == ["premium_60s", "premium_60s", "premium_60s"]
    assert families[6:9] == ["funding_start", "funding_start", "funding_start"]
    assert families[9:12] == ["oi_5m", "oi_5m", "oi_5m"]

    # Symbols within same family at same due time must be sorted lexicographically
    assert [s.canonical_symbol for s in start_slots[:3]] == ["BTCUSDT", "ETHUSDT", "REEFUSDT"]


def _make_client_core(profile_id: str, symbol: str = "BTCUSDT") -> dict[str, Any]:
    base_core = E_A_PROFILE_CORES[profile_id]
    derived = derive_event_profile_core(
        event_id="e" * 64,
        source_article_id="123456",
        source_detail_revision_id="rev_1",
        canonical_symbol=symbol,
        base_e_a_manifest_id="a" * 64,
        base_e_a_profile_id=profile_id,
        base_e_a_profile_attestation_sha256=compute_profile_attestation_sha256(base_core),
        base_e_a_profile_core=base_core,
    )
    return derived.http_profile_core


def test_public_client_no_redirect():
    def redirect_handler(req: urllib.request.Request):
        return _MockResponse(b"Moved", status=302, headers={"Location": "https://other.com"})

    client = Stage16EBPublicClient(opener=_MockOpener(redirect_handler))
    core = _make_client_core("binance_usdm_rest_depth_v1")
    res = client.fetch(core)
    assert res.outcome_kind == "redirect_rejected"
    assert res.raw_body is None
    assert res.http_status == 302


def test_public_client_timeout_and_transport():
    def timeout_handler(req: urllib.request.Request):
        raise socket.timeout("timed out")

    client = Stage16EBPublicClient(opener=_MockOpener(timeout_handler))
    core = _make_client_core("binance_usdm_rest_depth_v1")
    res = client.fetch(core)
    assert res.outcome_kind == "request_timeout"
    assert res.http_status is None
    assert res.raw_body is None

    def transport_handler(req: urllib.request.Request):
        raise urllib.error.URLError("Connection refused")

    client2 = Stage16EBPublicClient(opener=_MockOpener(transport_handler))
    res2 = client2.fetch(core)
    assert res2.outcome_kind == "transport_error"
    assert res2.raw_body is None


def test_public_client_oversized_body_and_differential_matrix():
    # 1. Depth profile: bound is 262144 bytes
    depth_core = _make_client_core("binance_usdm_rest_depth_v1")
    assert depth_core["max_raw_response_bytes"] == 262144

    depth_body_exact = b"{}" + b" " * (262144 - 2)
    client_depth_ok = Stage16EBPublicClient(opener=_MockOpener(lambda req: _MockResponse(depth_body_exact)))
    res_depth_ok = client_depth_ok.fetch(depth_core)
    assert res_depth_ok.outcome_kind == "response_verified"
    assert res_depth_ok.raw_body == depth_body_exact

    depth_body_oversized = b"{}" + b" " * (262145 - 2)
    client_depth_over = Stage16EBPublicClient(opener=_MockOpener(lambda req: _MockResponse(depth_body_oversized)))
    res_depth_over = client_depth_over.fetch(depth_core)
    assert res_depth_over.outcome_kind == "raw_size_exceeded"
    assert res_depth_over.raw_body is None

    # 2. Premium index profile: bound is 32768 bytes
    premium_core = _make_client_core("binance_usdm_rest_premium_index_v1")
    assert premium_core["max_raw_response_bytes"] == 32768

    premium_body_exact = b"{}" + b" " * (32768 - 2)
    client_premium_ok = Stage16EBPublicClient(opener=_MockOpener(lambda req: _MockResponse(premium_body_exact)))
    res_premium_ok = client_premium_ok.fetch(premium_core)
    assert res_premium_ok.outcome_kind == "response_verified"
    assert res_premium_ok.raw_body == premium_body_exact

    premium_body_oversized = b"{}" + b" " * (32769 - 2)
    client_premium_over = Stage16EBPublicClient(opener=_MockOpener(lambda req: _MockResponse(premium_body_oversized)))
    res_premium_over = client_premium_over.fetch(premium_core)
    assert res_premium_over.outcome_kind == "raw_size_exceeded"
    assert res_premium_over.raw_body is None


def test_public_client_raw_response_bound_validation():
    depth_core = _make_client_core("binance_usdm_rest_depth_v1")

    # Missing max_raw_response_bytes
    core_missing = dict(depth_core)
    del core_missing["max_raw_response_bytes"]
    opener = _MockOpener(lambda req: _MockResponse(b"{}"))
    client = Stage16EBPublicClient(opener=opener)
    with pytest.raises(ValueError, match="profile_core_raw_response_bound_invalid"):
        client.fetch(core_missing)
    assert len(opener.calls) == 0

    # Invalid types or values: True (bool), string, 0, -1
    for invalid_val in (True, "32768", 0, -1):
        core_invalid = dict(depth_core)
        core_invalid["max_raw_response_bytes"] = invalid_val
        opener_inv = _MockOpener(lambda req: _MockResponse(b"{}"))
        client_inv = Stage16EBPublicClient(opener=opener_inv)
        with pytest.raises(ValueError, match="profile_core_raw_response_bound_invalid"):
            client_inv.fetch(core_invalid)
        assert len(opener_inv.calls) == 0


def test_public_client_content_encoding():
    def gzip_handler(req: urllib.request.Request):
        return _MockResponse(b"compressed", status=200, headers={"Content-Encoding": "gzip"})

    client = Stage16EBPublicClient(opener=_MockOpener(gzip_handler))
    core = _make_client_core("binance_usdm_rest_depth_v1")
    res = client.fetch(core)
    assert res.outcome_kind == "content_encoding_invalid"
    assert res.raw_body is None


def test_public_client_verified_and_validation():
    payload = {
        "lastUpdateId": 123456,
        "E": 1700000001000,
        "T": 1700000000500,
        "bids": [["100.0", "1.0"]],
        "asks": [["101.0", "2.0"]],
    }
    raw = json.dumps(payload).encode("utf-8")

    def ok_handler(req: urllib.request.Request):
        return _MockResponse(raw, status=200, headers={"Content-Type": "application/json"})

    client = Stage16EBPublicClient(opener=_MockOpener(ok_handler))
    core = _make_client_core("binance_usdm_rest_depth_v1")
    res = client.fetch(core)
    assert res.outcome_kind == "response_verified"
    assert res.raw_body == raw
    assert res.headers_subset.get("content-type") == "application/json"


def test_validate_event_response_schema_and_time():
    # Premium index schema for REEFUSDT
    schema = {
        "root_type": "object",
        "root_array": None,
        "required_fields": {
            "estimatedSettlePrice": "decimal_string",
            "indexPrice": "decimal_string",
            "interestRate": "decimal_string",
            "lastFundingRate": "decimal_string",
            "markPrice": "decimal_string",
            "nextFundingTime": "ms_timestamp",
            "symbol": "literal_REEFUSDT",
            "time": "ms_timestamp",
        },
    }
    time_semantics = {
        "nextFundingTime": "next_scheduled_funding_time_ms",
        "time": "payload_observation_time_ms",
    }

    valid_payload = {
        "estimatedSettlePrice": "0.001",
        "indexPrice": "0.001",
        "interestRate": "0.0001",
        "lastFundingRate": "0.0001",
        "markPrice": "0.001",
        "nextFundingTime": 1700000000000,
        "symbol": "REEFUSDT",
        "time": 1699999000000,
    }

    ok, err = validate_event_response_schema(schema, valid_payload)
    assert ok is True
    assert err is None

    ok_t, err_t = validate_event_response_time(time_semantics, valid_payload)
    assert ok_t is True
    assert err_t is None

    # Mismatched literal symbol
    bad_symbol_payload = dict(valid_payload, symbol="BTCUSDT")
    ok, err = validate_event_response_schema(schema, bad_symbol_payload)
    assert ok is False
    assert "literal_REEFUSDT" in (err or "")

    # Invalid timestamp
    bad_time_payload = dict(valid_payload, time="not_an_int")
    ok, err = validate_event_response_schema(schema, bad_time_payload)
    assert ok is False

    # Missing field
    missing_field = dict(valid_payload)
    del missing_field["markPrice"]
    ok, err = validate_event_response_schema(schema, missing_field)
    assert ok is False
