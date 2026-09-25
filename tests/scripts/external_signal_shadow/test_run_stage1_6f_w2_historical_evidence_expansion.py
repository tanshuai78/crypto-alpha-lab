"""Tests for Stage 1.6F-W2 historical evidence expansion collector script.

Invariants: INV-W2E01, INV-W2E04, INV-W2E05, INV-W2E06, INV-W2E08, INV-W2E09, INV-W2E11, INV-W2E12, INV-W2E13.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict

import pytest

import scripts.external_signal_shadow.run_stage1_6f_w2_historical_evidence_expansion as collector
import src.research.external_signal_shadow.stage1_6f_w2_evidence_source as source
from configs.base import (
    EXCHANGE_TIMEOUT_MS,
    EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT,
)
from tests.research.external_signal_shadow.stage1_6f_w2_test_support import (
    B_SOURCE_EXPORT_RELATIVE,
    C_COMPLETED_ROOT_RELATIVE,
    CANONICAL_002_RELATIVE_PATH,
    COVERAGE_MATRIX_RELATIVE,
    W2_DESIGN_PATH,
    W2_DESIGN_SHA,
    W2_PLAN_PATH,
    W2_PLAN_SHA,
    FakeResponse,
    create_canonical_project_mirror,
    create_test_network_authorization,
)

EXACT_FETCH_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data/futures/um/daily/klines/1000XUSDT/1h/1000XUSDT-1h-2025-01-20.zip"


@pytest.fixture(scope="module")
def canonical_mirror(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("canonical_w2_mirror_collector")
    return create_canonical_project_mirror(base)


@pytest.fixture
def canonical_w2_inputs(canonical_mirror: Path, tmp_path: Path) -> Dict[str, Any]:
    auth_path = tmp_path / "test_w2_network_auth.json"
    auth_file, auth_sha = create_test_network_authorization(
        auth_path,
        run_id="w2_test_run_001",
    )
    c_002_manifest = canonical_mirror / CANONICAL_002_RELATIVE_PATH / "candidate_manifest.json"
    sha_before = hashlib.sha256(c_002_manifest.read_bytes()).hexdigest()

    # Pre-derive authority to obtain lexicographic fetch URLs
    authority = source.derive_w2_authority_inputs(
        project_root=canonical_mirror,
        c_completed_root=canonical_mirror / C_COMPLETED_ROOT_RELATIVE,
        b_source_export=canonical_mirror / B_SOURCE_EXPORT_RELATIVE,
        canonical_002_root=canonical_mirror / CANONICAL_002_RELATIVE_PATH,
        coverage_matrix=canonical_mirror / COVERAGE_MATRIX_RELATIVE,
        approved_design_path=canonical_mirror / W2_DESIGN_PATH,
        approved_design_sha=W2_DESIGN_SHA,
        approved_plan_path=canonical_mirror / W2_PLAN_PATH,
        approved_plan_sha=W2_PLAN_SHA,
        network_authorization_path=auth_path,
        network_authorization_sha=auth_sha,
    )
    request_set = source.derive_w2_request_set(authority)
    fetch_urls_lex = sorted([
        p["exact_source_url"] for p in request_set.physical_records
        if p["acquisition_method"] == "network_get"
    ])

    return {
        "project_root": canonical_mirror,
        "c_completed_root": canonical_mirror / C_COMPLETED_ROOT_RELATIVE,
        "b_source_export": canonical_mirror / B_SOURCE_EXPORT_RELATIVE,
        "canonical_002_root": canonical_mirror / CANONICAL_002_RELATIVE_PATH,
        "coverage_matrix": canonical_mirror / COVERAGE_MATRIX_RELATIVE,
        "approved_design_path": canonical_mirror / W2_DESIGN_PATH,
        "approved_design_sha": W2_DESIGN_SHA,
        "approved_plan_path": canonical_mirror / W2_PLAN_PATH,
        "approved_plan_sha": W2_PLAN_SHA,
        "network_authorization_path": auth_path,
        "network_authorization_sha": auth_sha,
        "canonical_002_manifest_sha_before": sha_before,
        "canonical_002_manifest_sha_after": lambda: hashlib.sha256(c_002_manifest.read_bytes()).hexdigest(),
        "fetch_urls_lexicographic": fetch_urls_lex,
    }


def test_offline_collector_writes_manifest_last_and_preserves_copy_source(
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    calls = []

    def transport(url: str) -> FakeResponse:
        calls.append(url)
        return FakeResponse(status=404, body=b"", headers={})

    output_root = tmp_path / "data/external_signal_shadow/stage1_6f/w2_evidence_candidates"
    run_id = "w2_test_run_001"

    kwargs = {k: v for k, v in canonical_w2_inputs.items() if not k.startswith("canonical_002_manifest_sha") and not k.startswith("fetch_urls")}
    result = collector.execute_w2_collection_run(
        **kwargs,
        output_root=output_root,
        run_id=run_id,
        transport=transport,
    )

    assert len(calls) == 171
    assert calls == canonical_w2_inputs["fetch_urls_lexicographic"]
    assert result["candidate_root_state"] == "collection_terminal_with_evidence_gaps"
    candidate_root = output_root / run_id
    assert (candidate_root / "candidate_manifest.json").is_file()
    assert canonical_w2_inputs["canonical_002_manifest_sha_before"] == canonical_w2_inputs["canonical_002_manifest_sha_after"]()

    # Reopen through source Class A validator
    verified = source.load_verified_w2_evidence(
        project_root=canonical_w2_inputs["project_root"],
        candidate_root=candidate_root,
        approved_design_path=canonical_w2_inputs["approved_design_path"],
        approved_design_sha=canonical_w2_inputs["approved_design_sha"],
        approved_plan_path=canonical_w2_inputs["approved_plan_path"],
        approved_plan_sha=canonical_w2_inputs["approved_plan_sha"],
        network_authorization_path=canonical_w2_inputs["network_authorization_path"],
        network_authorization_sha=canonical_w2_inputs["network_authorization_sha"],
    )
    assert verified.candidate_root_state == "collection_terminal_with_evidence_gaps"
    assert len(verified.physical_source_objects) == 180


def test_public_archive_opener_refuses_proxy_redirect_cookie_and_auth():
    opener = collector.build_public_archive_opener()
    assert any(
        isinstance(handler, urllib.request.ProxyHandler) and handler.proxies == {}
        for handler in opener.handlers
    )
    assert any(isinstance(handler, collector.NoRedirectHandler) for handler in opener.handlers)
    redirect_handlers = [
        handler for handler in opener.handlers
        if isinstance(handler, urllib.request.HTTPRedirectHandler)
    ]
    assert len(redirect_handlers) == 1
    assert isinstance(redirect_handlers[0], collector.NoRedirectHandler)
    forbidden = (
        urllib.request.HTTPCookieProcessor,
        urllib.request.HTTPBasicAuthHandler,
        urllib.request.HTTPDigestAuthHandler,
        urllib.request.ProxyBasicAuthHandler,
        urllib.request.ProxyDigestAuthHandler,
    )
    assert not any(isinstance(handler, forbidden) for handler in opener.handlers)


def test_real_transport_builds_production_opener_and_attempts_exactly_once(monkeypatch):
    calls = []

    class SpyOpener:
        handlers = []

        def open(self, request, *, timeout):
            calls.append((request, timeout))
            raise urllib.error.HTTPError(request.full_url, 302, "redirect", {}, None)

    monkeypatch.setattr(collector, "build_public_archive_opener", lambda: SpyOpener())
    with pytest.raises(urllib.error.HTTPError) as raised:
        collector.open_public_archive_get(EXACT_FETCH_URL)
    assert raised.value.code == 302
    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.get_method() == "GET"
    assert request.full_url == EXACT_FETCH_URL
    assert request.get_header("User-agent") == EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT
    assert timeout == EXCHANGE_TIMEOUT_MS / 1000.0


def test_uninjected_collector_routes_fetches_to_production_transport(
    monkeypatch,
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    calls = []

    def production_transport(url: str) -> FakeResponse:
        calls.append(url)
        return FakeResponse(status=404, body=b"", headers={})

    monkeypatch.setattr(collector, "open_public_archive_get", production_transport)
    monkeypatch.setattr(collector.time, "sleep", lambda s: None)
    kwargs = {k: v for k, v in canonical_w2_inputs.items() if not k.startswith("canonical_002_manifest_sha") and not k.startswith("fetch_urls")}
    collector.execute_w2_collection_run(
        **kwargs,
        output_root=tmp_path / "data/external_signal_shadow/stage1_6f/w2_evidence_candidates",
        run_id="w2_test_run_001",
        transport=None,
    )
    assert calls == canonical_w2_inputs["fetch_urls_lexicographic"]


def test_collector_enforces_free_space_guard(
    monkeypatch,
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    calls = []

    def transport(url: str) -> FakeResponse:
        calls.append(url)
        return FakeResponse(status=404, body=b"", headers={})

    # Mock free space to be 1 byte less than minimum
    class MockStatVFS:
        f_bavail = 100
        f_frsize = 100  # 10,000 bytes free

    import os
    monkeypatch.setattr(os, "statvfs", lambda p: MockStatVFS())

    kwargs = {k: v for k, v in canonical_w2_inputs.items() if not k.startswith("canonical_002_manifest_sha") and not k.startswith("fetch_urls")}
    with pytest.raises(collector.W2CollectionError, match="STOP=w2_insufficient_disk_space"):
        collector.execute_w2_collection_run(
            **kwargs,
            output_root=tmp_path / "data/external_signal_shadow/stage1_6f/w2_evidence_candidates",
            run_id="w2_test_run_001",
            transport=transport,
        )
    assert len(calls) == 0


def test_collector_collision_fails_closed(
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    output_root = tmp_path / "data/external_signal_shadow/stage1_6f/w2_evidence_candidates"
    candidate_root = output_root / "w2_test_run_001"
    candidate_root.mkdir(parents=True, exist_ok=True)

    kwargs = {k: v for k, v in canonical_w2_inputs.items() if not k.startswith("canonical_002_manifest_sha") and not k.startswith("fetch_urls")}
    with pytest.raises(collector.W2CollectionError, match="STOP=w2_candidate_root_already_exists"):
        collector.execute_w2_collection_run(
            **kwargs,
            output_root=output_root,
            run_id="w2_test_run_001",
            transport=lambda u: FakeResponse(404, b""),
        )


def test_cli_requires_explicit_public_readonly_and_never_self_attests(
    monkeypatch,
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("collector must not dispatch")

    monkeypatch.setattr(collector, "execute_w2_collection_run", fail_if_called)

    argv_base = [
        "--project-root", str(canonical_w2_inputs["project_root"]),
        "--c-completed-root", str(canonical_w2_inputs["c_completed_root"]),
        "--b-source-export", str(canonical_w2_inputs["b_source_export"]),
        "--canonical-002-root", str(canonical_w2_inputs["canonical_002_root"]),
        "--coverage-matrix", str(canonical_w2_inputs["coverage_matrix"]),
        "--output-root", str(tmp_path / "w2_candidates"),
        "--run-id", "w2_test_run_001",
        "--approved-design-path", str(canonical_w2_inputs["approved_design_path"]),
        "--approved-design-sha", str(canonical_w2_inputs["approved_design_sha"]),
        "--approved-plan-path", str(canonical_w2_inputs["approved_plan_path"]),
        "--approved-plan-sha", str(canonical_w2_inputs["approved_plan_sha"]),
        "--network-authorization-path", str(canonical_w2_inputs["network_authorization_path"]),
        "--network-authorization-sha", str(canonical_w2_inputs["network_authorization_sha"]),
    ]

    # 1. Missing --live-public-readonly must exit non-zero
    assert collector.main(argv_base) != 0

    # 2. Text check: no self-attestation or audit publication in collector script
    text = Path(collector.__file__).read_text(encoding="utf-8")
    assert "collection_attestation" not in text
    assert "audit_receipt_writer" not in text
    assert "audit_publisher" not in text
    assert "audit publisher" not in text


def test_transport_exception_sets_response_observed_at_ms_to_none_and_closes_stream(
    monkeypatch,
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    monkeypatch.setattr(collector.time, "sleep", lambda s: None)
    closed = []

    class FakeCloseableResponse(FakeResponse):
        def close(self):
            closed.append(True)

    calls = 0

    def transport(url: str):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionResetError("network connection reset")
        return FakeCloseableResponse(status=404, body=b"", headers={})

    output_root = tmp_path / "inconclusive_w2_candidates"
    run_id = "w2_test_run_001"
    kwargs = {
        k: v for k, v in canonical_w2_inputs.items()
        if not k.startswith("canonical_002_manifest_sha") and not k.startswith("fetch_urls")
    }
    result = collector.execute_w2_collection_run(
        **kwargs,
        output_root=output_root,
        run_id=run_id,
        transport=transport,
    )
    manifest = json.loads((output_root / run_id / "candidate_manifest.json").read_text(encoding="utf-8"))
    phys = manifest["physical_source_objects"]
    inconclusive = [p for p in phys if p["fetch_status"] == "transport_inconclusive"]
    assert len(inconclusive) == 1
    assert inconclusive[0]["response_observed_at_ms"] is None
    assert inconclusive[0]["http_status_or_transport_error"] == "network connection reset"
    assert len(closed) == 170
    assert result["candidate_root_state"] == "collection_terminal_with_evidence_gaps"


def test_atomic_write_file_retries_on_short_write_and_fails_closed_on_zero_write(tmp_path: Path, monkeypatch):
    target = tmp_path / "test_atomic.txt"
    data = b"0123456789abcdef"

    real_write = collector.os.write
    calls = []

    def mock_short_write(fd, buf):
        calls.append(len(buf))
        if len(calls) == 1:
            return real_write(fd, buf[:7])
        return real_write(fd, buf)

    monkeypatch.setattr(collector.os, "write", mock_short_write)
    collector._atomic_write_file(target, data)
    assert target.read_bytes() == data
    assert len(calls) >= 2

    # Zero write must fail closed
    def mock_zero_write(fd, buf):
        return 0

    monkeypatch.setattr(collector.os, "write", mock_zero_write)
    with pytest.raises(collector.W2CollectionError, match="STOP=w2_write_failed:zero_bytes_written"):
        collector._atomic_write_file(tmp_path / "zero.txt", data)


def test_collector_retention_and_reader_verification_for_archive_invalid_and_csv_invalid(
    monkeypatch,
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    monkeypatch.setattr(collector.time, "sleep", lambda s: None)
    import io
    import zipfile

    corrupt_zip_bytes = b"corrupted zip bytes that cannot be opened as a zip file"
    saved_header_only_zip_bytes = b""
    calls = 0

    raw_header_bytes = b"open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"

    def transport(url: str):
        nonlocal calls, saved_header_only_zip_bytes
        calls += 1
        if calls == 1:
            return FakeResponse(status=200, body=corrupt_zip_bytes, headers={})
        elif calls == 2:
            expected_csv = url.split("/")[-1].replace(".zip", ".csv")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                zf.writestr(
                    expected_csv,
                    raw_header_bytes,
                )
            saved_header_only_zip_bytes = buf.getvalue()
            return FakeResponse(status=200, body=saved_header_only_zip_bytes, headers={})
        return FakeResponse(status=404, body=b"", headers={})

    output_root = tmp_path / "retention_w2_candidates"
    run_id = "w2_test_run_001"
    kwargs = {
        k: v for k, v in canonical_w2_inputs.items()
        if not k.startswith("canonical_002_manifest_sha") and not k.startswith("fetch_urls")
    }
    result = collector.execute_w2_collection_run(
        **kwargs,
        output_root=output_root,
        run_id=run_id,
        transport=transport,
    )
    assert result["candidate_root_state"] == "collection_terminal_with_evidence_gaps"
    candidate_root = output_root / run_id
    manifest = json.loads((candidate_root / "candidate_manifest.json").read_text(encoding="utf-8"))
    phys = manifest["physical_source_objects"]

    # 1. Check archive_invalid
    arch_invalids = [p for p in phys if p["fetch_status"] == "archive_invalid"]
    assert len(arch_invalids) == 1
    ai = arch_invalids[0]
    assert ai["http_status_or_transport_error"] == 200
    assert ai["zip_relative_path"] == f"zips/{ai['physical_source_object_id']}.zip"
    assert (candidate_root / ai["zip_relative_path"]).is_file()
    assert (candidate_root / ai["zip_relative_path"]).read_bytes() == corrupt_zip_bytes
    assert ai["zip_byte_length"] == len(corrupt_zip_bytes)
    assert ai["csv_relative_path"] is None
    assert not (candidate_root / f"csvs/{ai['physical_source_object_id']}.csv").exists()
    assert ai["csv_row_count"] == 0

    # 2. Check csv_invalid
    csv_invalids = [p for p in phys if p["fetch_status"] == "csv_invalid"]
    assert len(csv_invalids) == 1
    ci = csv_invalids[0]
    assert ci["http_status_or_transport_error"] == 200
    assert ci["zip_relative_path"] == f"zips/{ci['physical_source_object_id']}.zip"
    assert (candidate_root / ci["zip_relative_path"]).is_file()
    assert (candidate_root / ci["zip_relative_path"]).read_bytes() == saved_header_only_zip_bytes
    assert ci["csv_relative_path"] == f"csvs/{ci['physical_source_object_id']}.csv"
    assert (candidate_root / ci["csv_relative_path"]).is_file()
    assert ci["csv_byte_length"] == len(raw_header_bytes)
    assert ci["csv_row_count"] == 0

    # 3. Strict reader MUST accept this candidate root with retained files
    verified = source.load_verified_w2_evidence(
        project_root=canonical_w2_inputs["project_root"],
        candidate_root=candidate_root,
        approved_design_path=canonical_w2_inputs["approved_design_path"],
        approved_design_sha=canonical_w2_inputs["approved_design_sha"],
        approved_plan_path=canonical_w2_inputs["approved_plan_path"],
        approved_plan_sha=canonical_w2_inputs["approved_plan_sha"],
        network_authorization_path=canonical_w2_inputs["network_authorization_path"],
        network_authorization_sha=canonical_w2_inputs["network_authorization_sha"],
    )
    assert verified.candidate_root_state == "collection_terminal_with_evidence_gaps"


def test_streaming_download_and_cap_probe(
    monkeypatch,
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    monkeypatch.setattr(collector.time, "sleep", lambda s: None)
    from configs.base import (
        EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES,
        EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES,
    )

    class OversizeStream:
        def __init__(self, size):
            self.remaining = size
            self.read_calls = []

        def read(self, n):
            self.read_calls.append(n)
            if self.remaining <= 0:
                return b""
            chunk_size = min(n, self.remaining)
            self.remaining -= chunk_size
            return b"x" * chunk_size

        def close(self):
            pass

    stream = OversizeStream(EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES + 10)
    fake_resp = FakeResponse(status=200, body=b"", headers={})
    fake_resp.read = stream.read
    fake_resp.close = stream.close

    calls = 0

    def transport(url: str):
        nonlocal calls
        calls += 1
        if calls == 1:
            return fake_resp
        return FakeResponse(status=404, body=b"", headers={})

    output_root = tmp_path / "oversize_w2_candidates"
    run_id = "w2_test_run_001"
    kwargs = {
        k: v for k, v in canonical_w2_inputs.items()
        if not k.startswith("canonical_002_manifest_sha") and not k.startswith("fetch_urls")
    }
    with pytest.raises(collector.W2CollectionError, match="STOP=w2_resource_budget_exceeded:zip_bytes_exceeded_cap"):
        collector.execute_w2_collection_run(
            **kwargs,
            output_root=output_root,
            run_id=run_id,
            transport=transport,
        )
    assert all(c <= EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES for c in stream.read_calls)
    assert 1 in stream.read_calls
    assert not (output_root / run_id / "candidate_manifest.json").exists()


def test_streaming_csv_extraction_and_cap_probe(
    monkeypatch,
    canonical_w2_inputs: Dict[str, Any],
    tmp_path: Path,
):
    monkeypatch.setattr(collector.time, "sleep", lambda s: None)
    import io
    import zipfile

    from configs.base import EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES

    calls = 0

    def transport(url: str):
        nonlocal calls
        calls += 1
        if calls == 1:
            expected_csv = url.split("/")[-1].replace(".zip", ".csv")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                # Compress an oversized payload (cap + 100 bytes) that fits in zip cap but exceeds CSV cap
                zf.writestr(expected_csv, b"0" * (EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES + 100))
            return FakeResponse(status=200, body=buf.getvalue(), headers={})
        return FakeResponse(status=404, body=b"", headers={})

    output_root = tmp_path / "oversize_csv_w2_candidates"
    run_id = "w2_test_run_001"
    kwargs = {
        k: v for k, v in canonical_w2_inputs.items()
        if not k.startswith("canonical_002_manifest_sha") and not k.startswith("fetch_urls")
    }
    with pytest.raises(collector.W2CollectionError, match="STOP=w2_resource_budget_exceeded:csv_bytes_exceeded_cap"):
        collector.execute_w2_collection_run(
            **kwargs,
            output_root=output_root,
            run_id=run_id,
            transport=transport,
        )
    assert not (output_root / run_id / "candidate_manifest.json").exists()




