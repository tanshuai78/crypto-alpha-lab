from __future__ import annotations

import hashlib
import io
import json
import socket
import ssl
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from research.external_signal_shadow.stage1_3_fixed_universe_diagnostic import (
    DiagnosticStopError,
    build_default_protocol,
    build_expected_archive_objects,
    parse_kline_zip_bytes,
)
from research.external_signal_shadow.stage1_3_models import HistoricalBar
from scripts.external_signal_shadow.run_stage1_3_fixed_universe_diagnostic import main

REPO_ROOT = Path(__file__).resolve().parents[3]
DESIGN_REL = "docs/designs/2026-11-23-stage1-3-fixed-universe-mean-return-diagnostic-design_CN.md"
PLAN_REL = "docs/plans/2026-11-24-stage1-3-fixed-universe-mean-return-diagnostic-implementation-plan_CN.md"
MS_15M = 15 * 60 * 1000
US_15M = 15 * 60 * 1_000_000


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_bar_to_csv_row(bar: HistoricalBar) -> str:
    open_us = bar.bar_start_ms * 1000
    close_us = open_us + US_15M - 1
    return (
        f"{open_us},{bar.open_price:.8f},{bar.high_price:.8f},"
        f"{bar.low_price:.8f},{bar.close_price:.8f},1.00000000,"
        f"{close_us},{bar.quote_volume:.8f},10,0.50000000,12.50000000,0"
    )


def _zip_csv(csv_filename: str, csv_text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(csv_filename, csv_text.encode("utf-8"))
    return buf.getvalue()


def _build_synthetic_archive_map() -> dict[str, bytes]:
    """Build synthetic 135 ZIP + 135 CHECKSUM payloads from canonical HistoricalBar instances."""
    protocol = build_default_protocol()
    objects = build_expected_archive_objects(protocol)
    payloads: dict[str, bytes] = {}
    eth_spike_start = int(datetime(2026, 6, 16, 11, 45, tzinfo=timezone.utc).timestamp() * 1000)
    eth_exit_start = int(datetime(2026, 6, 16, 16, 0, tzinfo=timezone.utc).timestamp() * 1000)

    for obj in objects:
        sym = obj["symbol"]
        rows: list[str] = []
        for d_iso in obj["expected_utc_dates"]:
            y, m, d = (int(x) for x in d_iso.split("-"))
            day_start_ms = int(datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000)
            for slot in range(96):
                b_start = day_start_ms + slot * MS_15M
                b_end = b_start + MS_15M
                if sym == "ETHUSDT" and b_start == eth_spike_start:
                    bar = HistoricalBar(sym, b_start, b_end, 100.0, 100.0, 100.0, 100.0, 325.0)
                elif sym == "ETHUSDT" and b_start == eth_exit_start:
                    bar = HistoricalBar(sym, b_start, b_end, 100.0, 102.0, 99.0, 101.0, 25.0)
                else:
                    bar = HistoricalBar(sym, b_start, b_end, 100.0, 100.0, 100.0, 100.0, 25.0)
                rows.append(_canonical_bar_to_csv_row(bar))
        zip_bytes = _zip_csv(obj["csv_filename"], "\n".join(rows) + "\n")
        chk_text = f"{_sha256_bytes(zip_bytes)}  {obj['zip_filename']}\n".encode("utf-8")
        payloads[obj["zip_url"]] = zip_bytes
        payloads[obj["checksum_url"]] = chk_text
    return payloads


class _MockResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
        chunks: list[bytes] | None = None,
    ) -> None:
        self.status = status
        self.headers = headers or {}
        if chunks is not None:
            self._chunks = list(chunks)
        else:
            self._chunks = [body] if body else []
        self._idx = 0
        self._offset = 0
        self.chunks_read = 0
        self.total_bytes_returned = 0

    def read(self, size: int = -1) -> bytes:
        if self._idx >= len(self._chunks):
            return b""
        cur = self._chunks[self._idx]
        if size is not None and size > 0:
            out = cur[self._offset : self._offset + size]
            self._offset += len(out)
            if self._offset >= len(cur):
                self._idx += 1
                self._offset = 0
        else:
            out = cur[self._offset :]
            self._idx += 1
            self._offset = 0
        if out:
            self.chunks_read += 1
            self.total_bytes_returned += len(out)
        return out


def _build_identity_responses() -> dict[str, bytes]:
    exchange_info = {
        "symbols": [
            {
                "symbol": sym,
                "status": "TRADING",
                "baseAsset": sym[:-4],
                "quoteAsset": "USDT",
                "isSpotTradingAllowed": True,
                "permissions": ["SPOT"],
            }
            for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
        ]
    }
    pre_warmup_ms = int(datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    in_window_ms = int(datetime(2026, 11, 18, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    # Build complete 50-article fixed pages (2 pages for 161 & 2 pages for 157) with strictly descending timestamps
    step_161 = (in_window_ms - pre_warmup_ms) // 99
    arts_161_all = [
        {
            "id": 1000 + i,
            "code": f"d161_{i:03d}",
            "title": f"Binance Will Delist UNRELATED{i:03d}USDT on 2026-11-20",
            "releaseDate": in_window_ms - i * step_161 if i < 99 else pre_warmup_ms,
        }
        for i in range(100)
    ]
    cms_161_p1 = {
        "code": "000000",
        "success": True,
        "data": {
            "catalogs": [
                {
                    "catalogId": 161,
                    "total": 447,
                    "articles": arts_161_all[:50],
                }
            ]
        },
    }
    cms_161_p2 = {
        "code": "000000",
        "success": True,
        "data": {
            "catalogs": [
                {
                    "catalogId": 161,
                    "total": 447,
                    "articles": arts_161_all[50:100],
                }
            ]
        },
    }
    step_157 = (in_window_ms - pre_warmup_ms) // 99
    arts_157_all = [
        {
            "id": 2000 + i,
            "code": f"m157_{i:03d}",
            "title": f"Wallet Maintenance Notice #{i:03d}",
            "releaseDate": in_window_ms - i * step_157 if i < 99 else pre_warmup_ms,
        }
        for i in range(100)
    ]
    cms_157_p1 = {
        "code": "000000",
        "success": True,
        "data": {
            "catalogs": [
                {
                    "catalogId": 157,
                    "total": 616,
                    "articles": arts_157_all[:50],
                }
            ]
        },
    }
    cms_157_p2 = {
        "code": "000000",
        "success": True,
        "data": {
            "catalogs": [
                {
                    "catalogId": 157,
                    "total": 616,
                    "articles": arts_157_all[50:100],
                }
            ]
        },
    }
    exch_5sym_url = (
        "https://api.binance.com/api/v3/exchangeInfo?"
        "symbols=%5B%22BTCUSDT%22%2C%22ETHUSDT%22%2C%22SOLUSDT%22%2C%22XRPUSDT%22%2C%22DOGEUSDT%22%5D"
    )
    return {
        exch_5sym_url: json.dumps(exchange_info).encode("utf-8"),
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=1&pageSize=50": json.dumps(
            cms_161_p1
        ).encode("utf-8"),
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=2&pageSize=50": json.dumps(
            cms_161_p2
        ).encode("utf-8"),
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=1&pageSize=50": json.dumps(
            cms_157_p1
        ).encode("utf-8"),
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=2&pageSize=50": json.dumps(
            cms_157_p2
        ).encode("utf-8"),
    }


@pytest.fixture(autouse=True)
def _block_real_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    def _forbid_socket(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Real socket network call is strictly forbidden in unit/CLI tests")

    monkeypatch.setattr(socket, "create_connection", _forbid_socket)
    monkeypatch.setattr(socket.socket, "connect", _forbid_socket)


def test_prepare_generates_135_object_manifest_zero_network_and_rejects_bad_inputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design_sha = _sha256_file(REPO_ROOT / DESIGN_REL)
    plan_sha = _sha256_file(REPO_ROOT / PLAN_REL)
    run_root = tmp_path / "run_001"
    manifest_path = tmp_path / "source_manifest.json"

    rc = main(
        [
            "prepare",
            "--repo-root",
            str(REPO_ROOT),
            "--run-root",
            str(run_root),
            "--output",
            str(manifest_path),
            "--design-sha256",
            design_sha,
            "--plan-sha256",
            plan_sha,
        ]
    )
    assert rc == 0
    assert manifest_path.exists()
    assert not run_root.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 1
    assert manifest["authority"]["design_sha256"] == design_sha
    assert manifest["authority"]["plan_sha256"] == plan_sha
    assert len(manifest["archive_objects"]) == 135
    assert manifest["resources"]["max_http_requests"] == 320
    assert manifest["resources"]["max_zip_bytes"] == 256 * 1024 * 1024
    assert len(manifest["symbol_identity_references"]["symbols"]) == 5
    # Must NOT fabricate future ZIP SHA-256 values
    assert all("zip_sha256" not in obj for obj in manifest["archive_objects"])

    # Reject existing run_root
    existing_root = tmp_path / "already_exists"
    existing_root.mkdir()
    rc_exist = main(
        [
            "prepare",
            "--repo-root",
            str(REPO_ROOT),
            "--run-root",
            str(existing_root),
            "--output",
            str(tmp_path / "m2.json"),
            "--design-sha256",
            design_sha,
            "--plan-sha256",
            plan_sha,
        ]
    )
    assert rc_exist != 0
    assert "STOP=existing_output_root" in capsys.readouterr().err

    # Reject wrong plan SHA
    rc_bad = main(
        [
            "prepare",
            "--repo-root",
            str(REPO_ROOT),
            "--run-root",
            str(tmp_path / "run_002"),
            "--output",
            str(tmp_path / "m3.json"),
            "--design-sha256",
            design_sha,
            "--plan-sha256",
            "0" * 64,
        ]
    )
    assert rc_bad != 0
    assert "STOP=source_manifest_mismatch" in capsys.readouterr().err


def test_fetch_and_analyze_canonical_end_to_end_and_idempotency_guards(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design_sha = _sha256_file(REPO_ROOT / DESIGN_REL)
    plan_sha = _sha256_file(REPO_ROOT / PLAN_REL)
    run_root = tmp_path / "run_e2e"
    manifest_path = tmp_path / "source_manifest.json"

    assert (
        main(
            [
                "prepare",
                "--repo-root",
                str(REPO_ROOT),
                "--run-root",
                str(run_root),
                "--output",
                str(manifest_path),
                "--design-sha256",
                design_sha,
                "--plan-sha256",
                plan_sha,
            ]
        )
        == 0
    )
    manifest_sha = _sha256_file(manifest_path)

    payloads = _build_synthetic_archive_map()
    payloads.update(_build_identity_responses())
    sleeps: list[float] = []

    def _mock_transport(url: str, timeout: float) -> _MockResponse:
        assert timeout <= 20.0
        if url not in payloads:
            return _MockResponse(status=404, body=b"not found")
        return _MockResponse(status=200, body=payloads[url])

    rc_fetch = main(
        ["fetch", "--manifest", str(manifest_path), "--manifest-sha256", manifest_sha],
        http_transport=_mock_transport,
        sleep_fn=sleeps.append,
    )
    assert rc_fetch == 0
    assert (run_root / "coverage.json").exists()
    cov = json.loads((run_root / "coverage.json").read_text(encoding="utf-8"))
    assert cov["coverage_qualified"] is True
    assert cov["total_archive_objects"] == 135
    assert cov["http_requests_used"] == 275  # 5 identity + 270 archive requests
    assert len(sleeps) >= 274
    assert all(s >= 1.0 for s in sleeps)

    # Re-running fetch on existing run_root must STOP=existing_output_root
    rc_fetch_again = main(
        ["fetch", "--manifest", str(manifest_path), "--manifest-sha256", manifest_sha],
        http_transport=_mock_transport,
        sleep_fn=sleeps.append,
    )
    assert rc_fetch_again != 0
    assert "STOP=existing_output_root" in capsys.readouterr().err

    # Analyze runs strictly offline (no http_transport passed)
    rc_analyze = main(
        ["analyze", "--manifest", str(manifest_path), "--manifest-sha256", manifest_sha],
    )
    assert rc_analyze == 0
    results_dir = run_root / "results"
    assert (results_dir / "ledger.jsonl").exists()
    assert (results_dir / "summary.json").exists()
    assert (results_dir / "EXECUTION_FINISHED").exists()

    summary = json.loads((results_dir / "summary.json").read_text(encoding="utf-8"))
    vol_s = summary["candidates"]["volume_spike_1h"]
    assert vol_s["counts"]["admitted"] == 1
    assert vol_s["mu_gross_bps"] == pytest.approx(100.0)
    assert vol_s["delta_bps"] == pytest.approx(100.0)

    # Re-running analyze when results/ exists must STOP=existing_output_root
    rc_analyze_again = main(
        ["analyze", "--manifest", str(manifest_path), "--manifest-sha256", manifest_sha],
    )
    assert rc_analyze_again != 0
    assert "STOP=existing_output_root" in capsys.readouterr().err


def test_parse_and_fetch_stop_on_checksum_nonfinite_unit_and_coverage_defects() -> None:
    day = "2026-11-01"
    day_start = int(datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp() * 1000)
    good_rows = [
        _canonical_bar_to_csv_row(
            HistoricalBar("BTCUSDT", day_start + i * MS_15M, day_start + (i + 1) * MS_15M, 100.0, 100.0, 100.0, 100.0, 25.0)
        )
        for i in range(96)
    ]
    zip_name = "BTCUSDT-15m-2026-11-01.zip"
    csv_name = "BTCUSDT-15m-2026-11-01.csv"
    good_zip = _zip_csv(csv_name, "\n".join(good_rows) + "\n")
    good_chk = f"{_sha256_bytes(good_zip)}  {zip_name}\n"

    # 1. Checksum hash mismatch -> STOP=checksum_mismatch
    with pytest.raises(DiagnosticStopError) as exc1:
        parse_kline_zip_bytes(
            good_zip,
            checksum_text=f"{'0' * 64}  {zip_name}\n",
            expected_zip_filename=zip_name,
            expected_csv_filename=csv_name,
            expected_symbol="BTCUSDT",
            expected_utc_dates=[day],
        )
    assert exc1.value.stop_code == "checksum_mismatch"

    # 2. Checksum target filename mismatch -> STOP=checksum_mismatch
    with pytest.raises(DiagnosticStopError) as exc2:
        parse_kline_zip_bytes(
            good_zip,
            checksum_text=f"{_sha256_bytes(good_zip)}  ETHUSDT-15m-2026-11-01.zip\n",
            expected_zip_filename=zip_name,
            expected_csv_filename=csv_name,
            expected_symbol="BTCUSDT",
            expected_utc_dates=[day],
        )
    assert exc2.value.stop_code == "checksum_mismatch"

    # 3. Nonfinite value (NaN / Inf) -> STOP=nonfinite_value
    nan_rows = list(good_rows)
    nan_rows[0] = nan_rows[0].replace("25.00000000", "NaN")
    nan_zip = _zip_csv(csv_name, "\n".join(nan_rows) + "\n")
    with pytest.raises(DiagnosticStopError) as exc3:
        parse_kline_zip_bytes(
            nan_zip,
            checksum_text=f"{_sha256_bytes(nan_zip)}  {zip_name}\n",
            expected_zip_filename=zip_name,
            expected_csv_filename=csv_name,
            expected_symbol="BTCUSDT",
            expected_utc_dates=[day],
        )
    assert exc3.value.stop_code == "nonfinite_value"

    # 4. Millisecond timestamp instead of microsecond -> STOP=coverage_incomplete
    ms_rows = [f"{day_start},100,100,100,100,1,{day_start + MS_15M - 1},25,10,0.5,12.5,0"] + good_rows[1:]
    ms_zip = _zip_csv(csv_name, "\n".join(ms_rows) + "\n")
    with pytest.raises(DiagnosticStopError) as exc4:
        parse_kline_zip_bytes(
            ms_zip,
            checksum_text=f"{_sha256_bytes(ms_zip)}  {zip_name}\n",
            expected_zip_filename=zip_name,
            expected_csv_filename=csv_name,
            expected_symbol="BTCUSDT",
            expected_utc_dates=[day],
        )
    assert exc4.value.stop_code == "coverage_incomplete"

    # 5. Missing bar -> STOP=coverage_incomplete
    short_zip = _zip_csv(csv_name, "\n".join(good_rows[:-1]) + "\n")
    with pytest.raises(DiagnosticStopError) as exc5:
        parse_kline_zip_bytes(
            short_zip,
            checksum_text=f"{_sha256_bytes(short_zip)}  {zip_name}\n",
            expected_zip_filename=zip_name,
            expected_csv_filename=csv_name,
            expected_symbol="BTCUSDT",
            expected_utc_dates=[day],
        )
    assert exc5.value.stop_code == "coverage_incomplete"

    # 6. Duplicate bar -> STOP=coverage_incomplete
    dup_zip = _zip_csv(csv_name, "\n".join(good_rows + [good_rows[0]]) + "\n")
    with pytest.raises(DiagnosticStopError) as exc6:
        parse_kline_zip_bytes(
            dup_zip,
            checksum_text=f"{_sha256_bytes(dup_zip)}  {zip_name}\n",
            expected_zip_filename=zip_name,
            expected_csv_filename=csv_name,
            expected_symbol="BTCUSDT",
            expected_utc_dates=[day],
        )
    assert exc6.value.stop_code == "coverage_incomplete"

    # 7. Valid parse produces 96 canonical HistoricalBar objects
    parsed, meta = parse_kline_zip_bytes(
        good_zip,
        checksum_text=good_chk,
        expected_zip_filename=zip_name,
        expected_csv_filename=csv_name,
        expected_symbol="BTCUSDT",
        expected_utc_dates=[day],
    )
    assert len(parsed) == 96
    assert meta["row_count"] == 96
    assert parsed[0].bar_start_ms == day_start
    assert parsed[0].bar_end_ms == day_start + MS_15M


def test_transport_enforces_request_limit_streaming_byte_limit_access_restricted_and_retries(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design_sha = _sha256_file(REPO_ROOT / DESIGN_REL)
    plan_sha = _sha256_file(REPO_ROOT / PLAN_REL)
    identity_resps = _build_identity_responses()

    def _prep(name: str) -> tuple[Path, Path, str]:
        rr = tmp_path / name
        mp = tmp_path / f"{name}_manifest.json"
        assert (
            main(
                [
                    "prepare",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--run-root",
                    str(rr),
                    "--output",
                    str(mp),
                    "--design-sha256",
                    design_sha,
                    "--plan-sha256",
                    plan_sha,
                ]
            )
            == 0
        )
        return rr, mp, _sha256_file(mp)

    # 1. Access restricted (HTTP 451 / 403 / 429) stops immediately with zero retry
    rr1, mp1, ms1 = _prep("run_451")
    calls_451: list[str] = []

    def _t_451(url: str, timeout: float) -> _MockResponse:
        calls_451.append(url)
        return _MockResponse(status=451, body=b"restricted")

    rc1 = main(
        ["fetch", "--manifest", str(mp1), "--manifest-sha256", ms1],
        http_transport=_t_451,
        sleep_fn=lambda _: None,
    )
    assert rc1 != 0
    assert "STOP=access_restricted" in capsys.readouterr().err
    assert len(calls_451) == 1

    # 2. Streaming download_byte_limit aborts BEFORE reading full oversized payload
    rr2, mp2, ms2 = _prep("run_bytelimit")
    # 260 chunks of 1 MiB + 1 byte -> exceeds 256 MiB mid-stream!
    one_mib = b"x" * (1024 * 1024)
    oversized_resp = _MockResponse(status=200, chunks=[one_mib] * 260)

    def _t_bytelimit(url: str, timeout: float) -> _MockResponse:
        if url in identity_resps:
            return _MockResponse(status=200, body=identity_resps[url])
        return oversized_resp

    rc2 = main(
        ["fetch", "--manifest", str(mp2), "--manifest-sha256", ms2],
        http_transport=_t_bytelimit,
        sleep_fn=lambda _: None,
    )
    assert rc2 != 0
    assert "STOP=download_byte_limit" in capsys.readouterr().err
    # Must stop strictly at the 256 MiB cap without consuming any byte past the cap!
    assert oversized_resp.total_bytes_returned == 256 * 1024 * 1024
    assert oversized_resp.total_bytes_returned < 260 * 1024 * 1024

    # 3. Request limit: 321st request must NEVER execute (test via manifest retry budget + cap check)
    # Also test TLS single retry per object -> 2nd consecutive failure stops and preserves failed attempt
    rr3, mp3, ms3 = _prep("run_tls_retry")
    tls_attempts: dict[str, int] = {}

    def _t_tls_twice(url: str, timeout: float) -> _MockResponse:
        if url in identity_resps:
            return _MockResponse(status=200, body=identity_resps[url])
        tls_attempts[url] = tls_attempts.get(url, 0) + 1
        raise ssl.SSLEOFError("simulated TLS EOF")

    rc3 = main(
        ["fetch", "--manifest", str(mp3), "--manifest-sha256", ms3],
        http_transport=_t_tls_twice,
        sleep_fn=lambda _: None,
    )
    assert rc3 != 0
    # Exactly 2 attempts on first archive object (1 initial + 1 retry), NEVER 3!
    assert list(tls_attempts.values()) == [2]
    assert (rr3 / "raw" / "failed_attempts").exists()

    # 4. Request limit explicit verification via 320-cap guard (simulate >320 via max_http_requests in transport check):
    # Verify that across >20 total TLS retries across distinct objects, fetch stops at retry #21 before exceeding 20 total retries
    rr4, mp4, ms4 = _prep("run_retry_cap")
    seen_retry_urls: dict[str, int] = {}
    payloads = _build_synthetic_archive_map()

    def _t_21_retries(url: str, timeout: float) -> _MockResponse:
        if url in identity_resps:
            return _MockResponse(status=200, body=identity_resps[url])
        count = seen_retry_urls.get(url, 0) + 1
        seen_retry_urls[url] = count
        if count == 1:
            raise TimeoutError("simulated timeout")
        return _MockResponse(status=200, body=payloads[url])

    rc4 = main(
        ["fetch", "--manifest", str(mp4), "--manifest-sha256", ms4],
        http_transport=_t_21_retries,
        sleep_fn=lambda _: None,
    )
    assert rc4 != 0
    assert "STOP=request_limit" in capsys.readouterr().err


def test_analyze_revalidates_manifest_source_identity_and_detects_tampering(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    design_sha = _sha256_file(REPO_ROOT / DESIGN_REL)
    plan_sha = _sha256_file(REPO_ROOT / PLAN_REL)
    run_root = tmp_path / "run_tamper"
    manifest_path = tmp_path / "source_manifest.json"
    assert (
        main(
            [
                "prepare",
                "--repo-root",
                str(REPO_ROOT),
                "--run-root",
                str(run_root),
                "--output",
                str(manifest_path),
                "--design-sha256",
                design_sha,
                "--plan-sha256",
                plan_sha,
            ]
        )
        == 0
    )
    manifest_sha = _sha256_file(manifest_path)

    # 1. Wrong manifest SHA on analyze -> STOP=source_manifest_mismatch
    rc_bad_sha = main(
        ["analyze", "--manifest", str(manifest_path), "--manifest-sha256", "f" * 64],
    )
    assert rc_bad_sha != 0
    assert "STOP=source_manifest_mismatch" in capsys.readouterr().err

    # 2. Tampered source_binding SHA inside manifest (with recomputed manifest SHA) -> STOP=source_identity_mismatch
    tampered_m = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered_m["source_bindings"][0]["sha256"] = "a" * 64
    tampered_mp = tmp_path / "tampered_src_manifest.json"
    tampered_mp.write_text(json.dumps(tampered_m), encoding="utf-8")
    rc_src_mismatch = main(
        ["analyze", "--manifest", str(tampered_mp), "--manifest-sha256", _sha256_file(tampered_mp)],
    )
    assert rc_src_mismatch != 0
    assert "STOP=source_identity_mismatch" in capsys.readouterr().err

    # 3. Fetch clean, then tamper one ZIP on disk before analyze -> STOP=checksum_mismatch
    payloads = _build_synthetic_archive_map()
    payloads.update(_build_identity_responses())
    assert (
        main(
            ["fetch", "--manifest", str(manifest_path), "--manifest-sha256", manifest_sha],
            http_transport=lambda url, timeout: _MockResponse(status=200, body=payloads[url]),
            sleep_fn=lambda _: None,
        )
        == 0
    )
    first_zip = next((run_root / "raw" / "archives").glob("*.zip"))
    first_zip.write_bytes(first_zip.read_bytes() + b"corrupt")

    rc_tamper = main(
        ["analyze", "--manifest", str(manifest_path), "--manifest-sha256", manifest_sha],
    )
    assert rc_tamper != 0
    assert "STOP=checksum_mismatch" in capsys.readouterr().err
    assert not (run_root / "results" / "EXECUTION_FINISHED").exists()


def test_bounded_fetcher_stops_before_321st_request(tmp_path: Path) -> None:
    from scripts.external_signal_shadow.run_stage1_3_fixed_universe_diagnostic import (
        _BoundedFetcher,
    )

    calls = 0

    def _ok_transport(url: str, timeout: float) -> _MockResponse:
        nonlocal calls
        calls += 1
        return _MockResponse(status=200, body=b"ok")

    fetcher = _BoundedFetcher(
        run_root=tmp_path / "cap320",
        max_requests=320,
        max_zip_bytes=256 * 1024 * 1024,
        min_interval_sec=1.0,
        timeout_sec=20.0,
        max_retries_per_object=1,
        max_total_retries=20,
        transport=_ok_transport,
        sleep_fn=lambda _: None,
    )
    url = "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/15m/BTCUSDT-15m-2026-11-01.zip.CHECKSUM"
    for i in range(320):
        fetcher.fetch_bytes(object_tag=f"obj_{i}", url=url, is_zip=False)
    assert calls == 320

    with pytest.raises(DiagnosticStopError) as exc:
        fetcher.fetch_bytes(object_tag="obj_320", url=url, is_zip=False)
    assert exc.value.stop_code == "request_limit"
    # 321st request MUST NOT fire
    assert calls == 320


def test_remediation_p1_01_rejects_incomplete_or_unspanned_cms_identity_catalog(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """P1-01: empty articles with total=500 or pages not spanning warmup_start must STOP=coverage_incomplete."""
    from scripts.external_signal_shadow.run_stage1_3_fixed_universe_diagnostic import (
        _verify_identity_payloads,
    )

    proto = build_default_protocol()
    id_resps = _build_identity_responses()
    exch_5sym_url = (
        "https://api.binance.com/api/v3/exchangeInfo?"
        "symbols=%5B%22BTCUSDT%22%2C%22ETHUSDT%22%2C%22SOLUSDT%22%2C%22XRPUSDT%22%2C%22DOGEUSDT%22%5D"
    )
    exch_bytes = id_resps[exch_5sym_url]
    cms_161_p2_bytes = id_resps[
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=2&pageSize=50"
    ]
    cms_157_p1_bytes = id_resps[
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=1&pageSize=50"
    ]
    cms_157_p2_bytes = id_resps[
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=2&pageSize=50"
    ]

    # Case 1: total=500, articles=[] (exact audit probe) -> direct _verify_identity_payloads MUST raise
    empty_cms_161 = json.dumps(
        {"code": "000000", "success": True, "data": {"catalogs": [{"catalogId": 161, "total": 500, "articles": []}]}}
    ).encode("utf-8")
    with pytest.raises(DiagnosticStopError) as exc1:
        _verify_identity_payloads(
            {
                "exchange_info_spot": exch_bytes,
                "cms_catalog_161_delisting_p1": empty_cms_161,
                "cms_catalog_161_delisting_p2": cms_161_p2_bytes,
                "cms_catalog_157_maintenance_p1": cms_157_p1_bytes,
                "cms_catalog_157_maintenance_p2": cms_157_p2_bytes,
            },
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc1.value.stop_code == "coverage_incomplete"

    # Case 2: non-empty articles, but oldest article is inside window (2026-09-01 > warmup_start 2026-06-08) while total=500
    mid_ms = int(datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    unspanned_cms_161 = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {
                "catalogs": [
                    {
                        "catalogId": 161,
                        "total": 500,
                        "articles": [
                            {"id": 1, "code": "x", "title": "Unrelated Delist", "releaseDate": mid_ms}
                        ],
                    }
                ]
            },
        }
    ).encode("utf-8")
    with pytest.raises(DiagnosticStopError) as exc2:
        _verify_identity_payloads(
            {
                "exchange_info_spot": exch_bytes,
                "cms_catalog_161_delisting_p1": unspanned_cms_161,
                "cms_catalog_161_delisting_p2": cms_161_p2_bytes,
                "cms_catalog_157_maintenance_p1": cms_157_p1_bytes,
                "cms_catalog_157_maintenance_p2": cms_157_p2_bytes,
            },
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc2.value.stop_code == "coverage_incomplete"

    # Case 3: end-to-end fetch stops right after identity checks (never fetches archive #1)
    design_sha = _sha256_file(REPO_ROOT / DESIGN_REL)
    plan_sha = _sha256_file(REPO_ROOT / PLAN_REL)
    rr = tmp_path / "p1_01_e2e_stop"
    mp = tmp_path / "p1_01_e2e_stop.json"
    assert (
        main(
            [
                "prepare",
                "--repo-root",
                str(REPO_ROOT),
                "--run-root",
                str(rr),
                "--output",
                str(mp),
                "--design-sha256",
                design_sha,
                "--plan-sha256",
                plan_sha,
            ]
        )
        == 0
    )
    payloads = dict(id_resps)
    payloads[
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=1&pageSize=50"
    ] = empty_cms_161
    called_urls: list[str] = []

    def _tr(url: str, timeout: float) -> _MockResponse:
        called_urls.append(url)
        return _MockResponse(status=200, body=payloads[url])

    rc = main(
        ["fetch", "--manifest", str(mp), "--manifest-sha256", _sha256_file(mp)],
        http_transport=_tr,
        sleep_fn=lambda _: None,
    )
    assert rc != 0
    assert "STOP=coverage_incomplete" in capsys.readouterr().err
    # Must stop immediately after the 5 identity requests without ever hitting data.binance.vision
    assert len(called_urls) == 5
    assert all("data.binance.vision" not in u for u in called_urls)


def test_remediation_p1_02_analyze_revalidates_identity_files_and_rejects_deleted_or_tampered(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """P1-02: deleting or tampering identity raw files after fetch must fail analyze before writing results."""
    design_sha = _sha256_file(REPO_ROOT / DESIGN_REL)
    plan_sha = _sha256_file(REPO_ROOT / PLAN_REL)
    payloads = _build_synthetic_archive_map()
    payloads.update(_build_identity_responses())

    def _prepare_and_fetch(name: str) -> tuple[Path, Path, str]:
        rr = tmp_path / name
        mp = tmp_path / f"{name}.json"
        assert (
            main(
                [
                    "prepare",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--run-root",
                    str(rr),
                    "--output",
                    str(mp),
                    "--design-sha256",
                    design_sha,
                    "--plan-sha256",
                    plan_sha,
                ]
            )
            == 0
        )
        msha = _sha256_file(mp)
        assert (
            main(
                ["fetch", "--manifest", str(mp), "--manifest-sha256", msha],
                http_transport=lambda url, timeout: _MockResponse(status=200, body=payloads[url]),
                sleep_fn=lambda _: None,
            )
            == 0
        )
        return rr, mp, msha

    # Case 1: delete exchange_info_spot.json -> must fail (exact audit probe)
    rr1, mp1, msha1 = _prepare_and_fetch("p1_02_delete")
    (rr1 / "raw" / "identity" / "exchange_info_spot.json").unlink()
    rc_del = main(["analyze", "--manifest", str(mp1), "--manifest-sha256", msha1])
    assert rc_del != 0
    assert "STOP=coverage_incomplete" in capsys.readouterr().err
    assert not (rr1 / "results" / "EXECUTION_FINISHED").exists()

    # Case 2: tamper exchange_info_spot.json bytes without updating coverage.json -> STOP=checksum_mismatch
    rr2, mp2, msha2 = _prepare_and_fetch("p1_02_tamper_bytes")
    exch_p = rr2 / "raw" / "identity" / "exchange_info_spot.json"
    exch_p.write_bytes(exch_p.read_bytes() + b" ")
    rc_tamp = main(["analyze", "--manifest", str(mp2), "--manifest-sha256", msha2])
    assert rc_tamp != 0
    assert "STOP=checksum_mismatch" in capsys.readouterr().err
    assert not (rr2 / "results" / "EXECUTION_FINISHED").exists()

    # Case 3: tamper exchange_info_spot.json semantically AND rewrite coverage sha256 -> semantic re-check must fail
    rr3, mp3, msha3 = _prepare_and_fetch("p1_02_tamper_semantic")
    exch_p3 = rr3 / "raw" / "identity" / "exchange_info_spot.json"
    bad_exch = json.loads(exch_p3.read_text(encoding="utf-8"))
    bad_exch["symbols"][0]["status"] = "BREAK"
    bad_bytes = json.dumps(bad_exch).encode("utf-8")
    exch_p3.write_bytes(bad_bytes)
    cov_p3 = rr3 / "coverage.json"
    cov3 = json.loads(cov_p3.read_text(encoding="utf-8"))
    for entry in cov3["identity_files"]:
        if entry["id"] == "exchange_info_spot":
            entry["sha256"] = _sha256_bytes(bad_bytes)
    cov_p3.write_text(json.dumps(cov3), encoding="utf-8")
    rc_sem = main(["analyze", "--manifest", str(mp3), "--manifest-sha256", msha3])
    assert rc_sem != 0
    assert "STOP=coverage_incomplete" in capsys.readouterr().err
    assert not (rr3 / "results" / "EXECUTION_FINISHED").exists()


def test_remediation_p1_03_analyze_rejects_external_absolute_traversal_and_symlink_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """P1-03: coverage paths pointing outside run_root (absolute, traversal, symlink) must fail before reading."""
    design_sha = _sha256_file(REPO_ROOT / DESIGN_REL)
    plan_sha = _sha256_file(REPO_ROOT / PLAN_REL)
    payloads = _build_synthetic_archive_map()
    payloads.update(_build_identity_responses())

    def _prepare_and_fetch(name: str) -> tuple[Path, Path, str]:
        rr = tmp_path / name
        mp = tmp_path / f"{name}.json"
        assert (
            main(
                [
                    "prepare",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--run-root",
                    str(rr),
                    "--output",
                    str(mp),
                    "--design-sha256",
                    design_sha,
                    "--plan-sha256",
                    plan_sha,
                ]
            )
            == 0
        )
        msha = _sha256_file(mp)
        assert (
            main(
                ["fetch", "--manifest", str(mp), "--manifest-sha256", msha],
                http_transport=lambda url, timeout: _MockResponse(status=200, body=payloads[url]),
                sleep_fn=lambda _: None,
            )
            == 0
        )
        return rr, mp, msha

    # Case 1: absolute external path with identical bytes (exact audit probe)
    rr1, mp1, msha1 = _prepare_and_fetch("p1_03_abs")
    cov_p1 = rr1 / "coverage.json"
    cov1 = json.loads(cov_p1.read_text(encoding="utf-8"))
    orig_zip = rr1 / cov1["archive_records"][0]["zip_relative_path"]
    ext_zip = tmp_path / "external_copy.zip"
    ext_zip.write_bytes(orig_zip.read_bytes())
    cov1["archive_records"][0]["zip_relative_path"] = str(ext_zip.resolve())
    cov_p1.write_text(json.dumps(cov1), encoding="utf-8")

    rc_abs = main(["analyze", "--manifest", str(mp1), "--manifest-sha256", msha1])
    assert rc_abs != 0
    assert "STOP=source_identity_mismatch" in capsys.readouterr().err
    assert not (rr1 / "results" / "EXECUTION_FINISHED").exists()

    # Case 2: relative '..' traversal escaping run_root
    rr2, mp2, msha2 = _prepare_and_fetch("p1_03_trav")
    cov_p2 = rr2 / "coverage.json"
    cov2 = json.loads(cov_p2.read_text(encoding="utf-8"))
    cov2["archive_records"][0]["zip_relative_path"] = "../external_copy.zip"
    cov_p2.write_text(json.dumps(cov2), encoding="utf-8")

    rc_trav = main(["analyze", "--manifest", str(mp2), "--manifest-sha256", msha2])
    assert rc_trav != 0
    assert "STOP=source_identity_mismatch" in capsys.readouterr().err

    # Case 3: symlink at expected path pointing outside run_root
    rr3, mp3, msha3 = _prepare_and_fetch("p1_03_sym")
    cov3 = json.loads((rr3 / "coverage.json").read_text(encoding="utf-8"))
    target_zip = rr3 / cov3["archive_records"][0]["zip_relative_path"]
    target_zip.unlink()
    target_zip.symlink_to(ext_zip)

    rc_sym = main(["analyze", "--manifest", str(mp3), "--manifest-sha256", msha3])
    assert rc_sym != 0
    assert "STOP=source_identity_mismatch" in capsys.readouterr().err


def test_remediation_p2_01_byte_cap_never_reads_past_limit_and_logs_exact_bytes(
    tmp_path: Path,
) -> None:
    """P2-01: cap=4 bytes must read <=4 bytes, report cumulative_zip_bytes=4, and write failed request log."""
    from scripts.external_signal_shadow.run_stage1_3_fixed_universe_diagnostic import (
        _BoundedFetcher,
    )

    run_root = tmp_path / "p2_01_cap4"
    resp = _MockResponse(status=200, body=b"12345")
    fetcher = _BoundedFetcher(
        run_root=run_root,
        max_requests=320,
        max_zip_bytes=4,
        min_interval_sec=1.0,
        timeout_sec=20.0,
        max_retries_per_object=1,
        max_total_retries=20,
        transport=lambda url, timeout: resp,
        sleep_fn=lambda _: None,
    )
    url = "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/15m/BTCUSDT-15m-2026-11-01.zip"
    with pytest.raises(DiagnosticStopError) as exc:
        fetcher.fetch_bytes(object_tag="BTCUSDT-15m-2026-11-01.zip", url=url, is_zip=True)
    assert exc.value.stop_code == "download_byte_limit"
    # Must NOT read 5th byte!
    assert resp.total_bytes_returned <= 4
    assert fetcher.zip_bytes_received == resp.total_bytes_returned
    assert fetcher.zip_bytes_received == 4
    # Must record failed request accurately in http_requests.jsonl
    log_lines = (run_root / "logs" / "http_requests.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 1
    rec = json.loads(log_lines[0])
    assert rec["bytes_received"] == 4
    assert rec["cumulative_zip_bytes"] == 4
    assert "download_byte_limit" in str(rec["error"])


def test_remediation_r2_p1_01_rejects_truncated_pagination_and_exact_symbol_delisting() -> None:
    """P1-01 r2: truncated non-empty pages (even spanning warmup) and exact-symbol delistings must STOP."""
    from scripts.external_signal_shadow.run_stage1_3_fixed_universe_diagnostic import (
        _verify_identity_payloads,
    )

    proto = build_default_protocol()
    id_resps = _build_identity_responses()
    exch_5sym_url = (
        "https://api.binance.com/api/v3/exchangeInfo?"
        "symbols=%5B%22BTCUSDT%22%2C%22ETHUSDT%22%2C%22SOLUSDT%22%2C%22XRPUSDT%22%2C%22DOGEUSDT%22%5D"
    )
    exch_bytes = id_resps[exch_5sym_url]
    url_161 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=1&pageSize=50"
    )
    url_161_p2 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=2&pageSize=50"
    )
    url_157_p1 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=1&pageSize=50"
    )
    url_157_p2 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=2&pageSize=50"
    )
    base_payloads = {
        "exchange_info_spot": exch_bytes,
        "cms_catalog_161_delisting_p1": id_resps[url_161],
        "cms_catalog_161_delisting_p2": id_resps[url_161_p2],
        "cms_catalog_157_maintenance_p1": id_resps[url_157_p1],
        "cms_catalog_157_maintenance_p2": id_resps[url_157_p2],
    }

    # Positive sanity: complete 50-article pages pass
    res_ok = _verify_identity_payloads(
        base_payloads,
        symbols=proto["symbols"],
        warmup_start_ms=proto["warmup_start_ms"],
        eval_end_ms=proto["eval_end_ms"],
    )
    assert res_ok["identity_checks_passed"] is True

    pre_warmup_ms = int(datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    in_window_ms = int(datetime(2026, 11, 18, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)

    # Case A: exact audit probe — catalog 161 total=447 with only 2 articles (spanning warmup) MUST fail
    trunc_161 = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {
                "catalogs": [
                    {
                        "catalogId": 161,
                        "total": 447,
                        "articles": [
                            {"id": 1, "code": "a1", "title": "Binance Will Delist UNRELATED", "releaseDate": in_window_ms},
                            {"id": 2, "code": "a2", "title": "Binance Will Delist OLDCOIN", "releaseDate": pre_warmup_ms},
                        ],
                    }
                ]
            },
        }
    ).encode("utf-8")
    p_trunc_161 = dict(base_payloads)
    p_trunc_161["cms_catalog_161_delisting_p1"] = trunc_161
    with pytest.raises(DiagnosticStopError) as exc_a:
        _verify_identity_payloads(
            p_trunc_161,
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc_a.value.stop_code == "coverage_incomplete"

    # Case B: exact audit probe — catalog 157 total=616 with 1 article on p1 and 1 article on p2 MUST fail
    p_trunc_157 = dict(base_payloads)
    p_trunc_157["cms_catalog_157_maintenance_p1"] = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {
                "catalogs": [
                    {
                        "catalogId": 157,
                        "total": 616,
                        "articles": [{"id": 11, "code": "m1", "title": "Maintenance 1", "releaseDate": in_window_ms}],
                    }
                ]
            },
        }
    ).encode("utf-8")
    p_trunc_157["cms_catalog_157_maintenance_p2"] = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {
                "catalogs": [
                    {
                        "catalogId": 157,
                        "total": 616,
                        "articles": [{"id": 12, "code": "m2", "title": "Maintenance 2", "releaseDate": pre_warmup_ms}],
                    }
                ]
            },
        }
    ).encode("utf-8")
    with pytest.raises(DiagnosticStopError) as exc_b:
        _verify_identity_payloads(
            p_trunc_157,
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc_b.value.stop_code == "coverage_incomplete"

    # Case C: duplicate p2 repeating p1 identically (50 articles each, total=616, only 50 unique) MUST fail
    p_dup_157 = dict(base_payloads)
    p_dup_157["cms_catalog_157_maintenance_p2"] = p_dup_157["cms_catalog_157_maintenance_p1"]
    with pytest.raises(DiagnosticStopError) as exc_c:
        _verify_identity_payloads(
            p_dup_157,
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc_c.value.stop_code == "coverage_incomplete"

    # Case D: exact audit probe — full valid catalog with title containing exact symbol "DOGEUSDT" MUST fail
    doge_161 = json.loads(id_resps[url_161].decode("utf-8"))
    doge_161["data"]["catalogs"][0]["articles"][0]["title"] = (
        "Notice of Removal of Spot Trading Pairs - DOGEUSDT"
    )
    p_doge = dict(base_payloads)
    p_doge["cms_catalog_161_delisting_p1"] = json.dumps(doge_161).encode("utf-8")
    with pytest.raises(DiagnosticStopError) as exc_d:
        _verify_identity_payloads(
            p_doge,
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc_d.value.stop_code == "coverage_incomplete"
    assert "DOGEUSDT" in exc_d.value.detail

    # Case E: genuinely complete small catalog (total=2, 2 articles on p1, 0 articles on p2) MUST pass
    p_small = dict(base_payloads)
    p_small["cms_catalog_157_maintenance_p1"] = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {
                "catalogs": [
                    {
                        "catalogId": 157,
                        "total": 2,
                        "articles": [
                            {"id": 21, "code": "s1", "title": "Wallet Maintenance A", "releaseDate": in_window_ms},
                            {"id": 22, "code": "s2", "title": "Wallet Maintenance B", "releaseDate": pre_warmup_ms},
                        ],
                    }
                ]
            },
        }
    ).encode("utf-8")
    p_small["cms_catalog_157_maintenance_p2"] = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {"catalogs": [{"catalogId": 157, "total": 2, "articles": []}]},
        }
    ).encode("utf-8")
    res_small = _verify_identity_payloads(
        p_small,
        symbols=proto["symbols"],
        warmup_start_ms=proto["warmup_start_ms"],
        eval_end_ms=proto["eval_end_ms"],
    )
    assert res_small["identity_checks_passed"] is True
    assert res_small["catalog_coverage"]["catalog_157_maintenance"]["full_catalog_fetched"] is True


def test_remediation_r2_p2_01_stream_read_timeout_logs_partial_bytes_and_obeys_retry_cap(
    tmp_path: Path,
) -> None:
    """P2-01 r2: mid-stream TimeoutError after partial bytes must log exact bytes/error and obey retry cap."""
    from scripts.external_signal_shadow.run_stage1_3_fixed_universe_diagnostic import (
        _BoundedFetcher,
    )

    class _TimeoutAfterTwoBytesResp:
        def __init__(self) -> None:
            self.status = 200
            self.headers: dict[str, str] = {}
            self._sent = False
            self.closed = False

        def read(self, size: int = -1) -> bytes:
            if not self._sent:
                self._sent = True
                return b"AB"[:size] if size > 0 else b"AB"
            raise TimeoutError("simulated mid-stream read timeout")

        def close(self) -> None:
            self.closed = True

    url = "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/15m/BTCUSDT-15m-2026-11-01.zip"

    # Case A: exact audit probe (2 bytes then TimeoutError, max_retries_per_object=0) -> STOP + 1 logged record
    rr1 = tmp_path / "p2_01_stream_timeout_noretry"
    resp1 = _TimeoutAfterTwoBytesResp()
    fetcher1 = _BoundedFetcher(
        run_root=rr1,
        max_requests=320,
        max_zip_bytes=1024,
        min_interval_sec=1.0,
        timeout_sec=20.0,
        max_retries_per_object=0,
        max_total_retries=20,
        transport=lambda u, t: resp1,
        sleep_fn=lambda _: None,
    )
    with pytest.raises(DiagnosticStopError) as exc1:
        fetcher1.fetch_bytes(object_tag="BTCUSDT-15m-2026-11-01.zip", url=url, is_zip=True)
    assert exc1.value.stop_code == "coverage_incomplete"
    assert resp1.closed is True
    assert fetcher1.zip_bytes_received == 2
    assert fetcher1.requests_used == 1
    lines1 = (rr1 / "logs" / "http_requests.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines1) == 1
    rec1 = json.loads(lines1[0])
    assert rec1["status_code"] == 200
    assert rec1["bytes_received"] == 2
    assert rec1["cumulative_zip_bytes"] == 2
    assert "TimeoutError" in str(rec1["error"])
    assert len(list((rr1 / "raw" / "failed_attempts").glob("*.json"))) == 1

    # Case B: retryable mid-stream TimeoutError succeeds on attempt 2 (max_retries_per_object=1)
    rr2 = tmp_path / "p2_01_stream_timeout_retry_ok"
    calls2 = 0

    def _tr2(u: str, t: float) -> Any:
        nonlocal calls2
        calls2 += 1
        if calls2 == 1:
            return _TimeoutAfterTwoBytesResp()
        return _MockResponse(status=200, body=b"WXYZ")

    fetcher2 = _BoundedFetcher(
        run_root=rr2,
        max_requests=320,
        max_zip_bytes=1024,
        min_interval_sec=1.0,
        timeout_sec=20.0,
        max_retries_per_object=1,
        max_total_retries=20,
        transport=_tr2,
        sleep_fn=lambda _: None,
    )
    data2, final_rec2 = fetcher2.fetch_bytes(object_tag="BTCUSDT-15m-2026-11-01.zip", url=url, is_zip=True)
    assert data2 == b"WXYZ"
    assert final_rec2["attempt"] == 2
    assert fetcher2.requests_used == 2
    assert fetcher2.retries_used == 1
    assert fetcher2.zip_bytes_received == 6
    lines2 = (rr2 / "logs" / "http_requests.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines2) == 2
    r2_fail = json.loads(lines2[0])
    r2_ok = json.loads(lines2[1])
    assert r2_fail["bytes_received"] == 2
    assert r2_fail["cumulative_zip_bytes"] == 2
    assert "TimeoutError" in str(r2_fail["error"])
    assert r2_ok["bytes_received"] == 4
    assert r2_ok["cumulative_zip_bytes"] == 6
    assert r2_ok["error"] is None

    # Case C: two consecutive mid-stream TimeoutErrors stop at retry cap with 2 logged failed records
    rr3 = tmp_path / "p2_01_stream_timeout_retry_exhausted"
    fetcher3 = _BoundedFetcher(
        run_root=rr3,
        max_requests=320,
        max_zip_bytes=1024,
        min_interval_sec=1.0,
        timeout_sec=20.0,
        max_retries_per_object=1,
        max_total_retries=20,
        transport=lambda u, t: _TimeoutAfterTwoBytesResp(),
        sleep_fn=lambda _: None,
    )
    with pytest.raises(DiagnosticStopError) as exc3:
        fetcher3.fetch_bytes(object_tag="BTCUSDT-15m-2026-11-01.zip", url=url, is_zip=True)
    assert exc3.value.stop_code == "coverage_incomplete"
    assert fetcher3.requests_used == 2
    assert fetcher3.retries_used == 1
    assert fetcher3.zip_bytes_received == 4
    lines3 = (rr3 / "logs" / "http_requests.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines3) == 2
    assert json.loads(lines3[0])["cumulative_zip_bytes"] == 2
    assert json.loads(lines3[1])["cumulative_zip_bytes"] == 4


def test_remediation_r3_p1_01_rejects_cross_page_total_change() -> None:
    """P1-01 r3: any cross-page total change (deletion/insertion shift) must STOP=coverage_incomplete."""
    from scripts.external_signal_shadow.run_stage1_3_fixed_universe_diagnostic import (
        _verify_identity_payloads,
    )

    proto = build_default_protocol()
    id_resps = _build_identity_responses()
    exch_5sym_url = (
        "https://api.binance.com/api/v3/exchangeInfo?"
        "symbols=%5B%22BTCUSDT%22%2C%22ETHUSDT%22%2C%22SOLUSDT%22%2C%22XRPUSDT%22%2C%22DOGEUSDT%22%5D"
    )
    url_161 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=1&pageSize=50"
    )
    url_161_p2 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=2&pageSize=50"
    )
    url_157_p1 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=1&pageSize=50"
    )
    url_157_p2 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=2&pageSize=50"
    )
    base_payloads = {
        "exchange_info_spot": id_resps[exch_5sym_url],
        "cms_catalog_161_delisting_p1": id_resps[url_161],
        "cms_catalog_161_delisting_p2": id_resps[url_161_p2],
        "cms_catalog_157_maintenance_p1": id_resps[url_157_p1],
        "cms_catalog_157_maintenance_p2": id_resps[url_157_p2],
    }

    # Construct exact audit deletion-shift probe:
    # Underlying catalog has 101 newest articles (index 50 is a DOGEUSDT delisting notice at page boundary).
    # Page 1 fetches [0..49] with total=616. Before Page 2, an unrelated item in [0..49] is deleted -> total=615,
    # so Page 2 offset 50 skips index 50 (the DOGEUSDT notice) and returns [51..100] (50 unique articles, descending dates).
    pre_warmup_ms = int(datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    in_window_ms = int(datetime(2026, 11, 18, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    step = (in_window_ms - pre_warmup_ms) // 100
    full_101 = [
        {
            "id": 3000 + i,
            "code": f"shift_{i:03d}",
            "title": (
                "Notice of Removal of Spot Trading Pairs - DOGEUSDT"
                if i == 50
                else f"Wallet Maintenance Notice #{i:03d}"
            ),
            "releaseDate": in_window_ms - i * step if i < 100 else pre_warmup_ms,
        }
        for i in range(101)
    ]

    p1_bytes = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {"catalogs": [{"catalogId": 157, "total": 616, "articles": full_101[:50]}]},
        }
    ).encode("utf-8")
    p2_shifted_bytes = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {"catalogs": [{"catalogId": 157, "total": 615, "articles": full_101[51:101]}]},
        }
    ).encode("utf-8")

    # Case 1: deletion shift (616 -> 615) skips boundary DOGEUSDT notice -> MUST fail closed
    p_del_shift = dict(base_payloads)
    p_del_shift["cms_catalog_157_maintenance_p1"] = p1_bytes
    p_del_shift["cms_catalog_157_maintenance_p2"] = p2_shifted_bytes
    with pytest.raises(DiagnosticStopError) as exc_del:
        _verify_identity_payloads(
            p_del_shift,
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc_del.value.stop_code == "coverage_incomplete"

    # Case 2: insertion shift (616 -> 617) with 1 overlapping boundary item -> MUST fail closed
    p2_ins_bytes = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {"catalogs": [{"catalogId": 157, "total": 617, "articles": full_101[49:99]}]},
        }
    ).encode("utf-8")
    p_ins_shift = dict(base_payloads)
    p_ins_shift["cms_catalog_157_maintenance_p1"] = p1_bytes
    p_ins_shift["cms_catalog_157_maintenance_p2"] = p2_ins_bytes
    with pytest.raises(DiagnosticStopError) as exc_ins:
        _verify_identity_payloads(
            p_ins_shift,
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc_ins.value.stop_code == "coverage_incomplete"

    # Control: stable pagination (total=616 on both pages) captures index 50 DOGEUSDT notice
    p2_stable_bytes = json.dumps(
        {
            "code": "000000",
            "success": True,
            "data": {"catalogs": [{"catalogId": 157, "total": 616, "articles": full_101[50:100]}]},
        }
    ).encode("utf-8")
    p_stable = dict(base_payloads)
    p_stable["cms_catalog_157_maintenance_p1"] = p1_bytes
    p_stable["cms_catalog_157_maintenance_p2"] = p2_stable_bytes
    with pytest.raises(DiagnosticStopError) as exc_ctrl:
        _verify_identity_payloads(
            p_stable,
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc_ctrl.value.stop_code == "coverage_incomplete"
    assert "DOGEUSDT" in exc_ctrl.value.detail


def test_remediation_r4_narrowed_5symbol_exchange_info_and_catalog_161_two_page_span() -> None:
    """R4: exchangeInfo narrowed to exact 5 symbols & Catalog 161 spans warmup across pages 1+2."""
    import urllib.parse

    from scripts.external_signal_shadow.run_stage1_3_fixed_universe_diagnostic import (
        IDENTITY_VERIFICATION_URLS,
        _verify_identity_payloads,
    )

    # 1. Verify exact 5 identity URLs & 5-symbol query parameter on exchangeInfo
    assert [x["id"] for x in IDENTITY_VERIFICATION_URLS] == [
        "exchange_info_spot",
        "cms_catalog_161_delisting_p1",
        "cms_catalog_161_delisting_p2",
        "cms_catalog_157_maintenance_p1",
        "cms_catalog_157_maintenance_p2",
    ]
    exch_url = IDENTITY_VERIFICATION_URLS[0]["url"]
    parsed = urllib.parse.urlparse(exch_url)
    assert parsed.scheme == "https"
    assert parsed.hostname == "api.binance.com"
    assert parsed.path == "/api/v3/exchangeInfo"
    qs = urllib.parse.parse_qs(parsed.query, strict_parsing=True)
    assert qs == {"symbols": ['["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"]']}

    assert (
        IDENTITY_VERIFICATION_URLS[2]["url"]
        == "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=2&pageSize=50"
    )

    # 2. Reproduce real 2026-11-23 boundary: Catalog 161 p1 oldest is 2026-06-09T08:30Z (> warmup 2026-06-08T00:00Z),
    # while p2 continues down to 2026-04-01T00:00Z (<= warmup) -> 2-page verification passes with 100 unique articles.
    proto = build_default_protocol()
    id_resps = _build_identity_responses()
    p1_newest_ms = int(datetime(2026, 11, 18, 5, 0, tzinfo=timezone.utc).timestamp() * 1000)
    p1_oldest_ms = int(datetime(2026, 6, 9, 8, 30, tzinfo=timezone.utc).timestamp() * 1000)
    p2_newest_ms = int(datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
    p2_oldest_ms = int(datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert p1_oldest_ms > proto["warmup_start_ms"]
    assert p2_oldest_ms <= proto["warmup_start_ms"]

    step1 = (p1_newest_ms - p1_oldest_ms) // 49
    arts_161_p1 = [
        {
            "id": 4000 + i,
            "code": f"r4_161_p1_{i:02d}",
            "title": f"Notice of Removal of Spot Trading Pairs - ALT{i:02d}",
            "releaseDate": p1_newest_ms - i * step1 if i < 49 else p1_oldest_ms,
        }
        for i in range(50)
    ]
    step2 = (p2_newest_ms - p2_oldest_ms) // 49
    arts_161_p2 = [
        {
            "id": 4100 + i,
            "code": f"r4_161_p2_{i:02d}",
            "title": f"Notice of Removal of Spot Trading Pairs - OLDALT{i:02d}",
            "releaseDate": p2_newest_ms - i * step2 if i < 49 else p2_oldest_ms,
        }
        for i in range(50)
    ]

    url_157_p1 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=1&pageSize=50"
    )
    url_157_p2 = (
        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=2&pageSize=50"
    )
    exch_bytes = id_resps[exch_url]
    payloads = {
        "exchange_info_spot": exch_bytes,
        "cms_catalog_161_delisting_p1": json.dumps(
            {"code": "000000", "success": True, "data": {"catalogs": [{"catalogId": 161, "total": 447, "articles": arts_161_p1}]}}
        ).encode("utf-8"),
        "cms_catalog_161_delisting_p2": json.dumps(
            {"code": "000000", "success": True, "data": {"catalogs": [{"catalogId": 161, "total": 447, "articles": arts_161_p2}]}}
        ).encode("utf-8"),
        "cms_catalog_157_maintenance_p1": id_resps[url_157_p1],
        "cms_catalog_157_maintenance_p2": id_resps[url_157_p2],
    }

    res = _verify_identity_payloads(
        payloads,
        symbols=proto["symbols"],
        warmup_start_ms=proto["warmup_start_ms"],
        eval_end_ms=proto["eval_end_ms"],
    )
    assert res["identity_checks_passed"] is True
    assert res["catalog_coverage"]["catalog_161_delisting"]["articles_collected"] == 100
    assert res["catalog_coverage"]["catalog_161_delisting"]["spans_warmup_boundary"] is True

    # 3. Cross-page total drift on Catalog 161 (447 vs 446) MUST fail closed
    bad_p2 = dict(payloads)
    bad_p2["cms_catalog_161_delisting_p2"] = json.dumps(
        {"code": "000000", "success": True, "data": {"catalogs": [{"catalogId": 161, "total": 446, "articles": arts_161_p2}]}}
    ).encode("utf-8")
    with pytest.raises(DiagnosticStopError) as exc_drift:
        _verify_identity_payloads(
            bad_p2,
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc_drift.value.stop_code == "coverage_incomplete"

    # 4. Extra unrequested symbol in narrowed exchangeInfo MUST fail closed
    extra_exch = json.loads(exch_bytes.decode("utf-8"))
    extra_exch["symbols"].append(
        {
            "symbol": "ADAUSDT",
            "status": "TRADING",
            "baseAsset": "ADA",
            "quoteAsset": "USDT",
            "isSpotTradingAllowed": True,
            "permissions": ["SPOT"],
        }
    )
    bad_exch = dict(payloads)
    bad_exch["exchange_info_spot"] = json.dumps(extra_exch).encode("utf-8")
    with pytest.raises(DiagnosticStopError) as exc_extra:
        _verify_identity_payloads(
            bad_exch,
            symbols=proto["symbols"],
            warmup_start_ms=proto["warmup_start_ms"],
            eval_end_ms=proto["eval_end_ms"],
        )
    assert exc_extra.value.stop_code == "coverage_incomplete"
