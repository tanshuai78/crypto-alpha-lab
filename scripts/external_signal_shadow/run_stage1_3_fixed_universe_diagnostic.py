#!/usr/bin/env python3
"""Bounded CLI for Stage 1.3 fixed-universe mean-return diagnostic.

Subcommands:
- prepare: offline metadata & 135-object source_manifest.json generation (zero network, zero data reads)
- fetch: bounded public read-only archive fetch + identity/integrity/coverage validation
- analyze: strictly offline re-verification + diagnostic ledger/summary generation
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research.external_signal_shadow.stage1_3_fixed_universe_diagnostic import (
    DiagnosticStopError,
    analyze_bars,
    build_default_protocol,
    build_expected_archive_objects,
    parse_kline_zip_bytes,
    validate_protocol,
    verify_base_and_safety_config,
)
from research.external_signal_shadow.stage1_3_models import HistoricalBar

DESIGN_REL_PATH = "docs/designs/2026-11-23-stage1-3-fixed-universe-mean-return-diagnostic-design_CN.md"
PLAN_REL_PATH = "docs/plans/2026-11-24-stage1-3-fixed-universe-mean-return-diagnostic-implementation-plan_CN.md"
SOURCE_BINDING_SPECS: tuple[tuple[str, str], ...] = (
    ("src/research/external_signal_shadow/stage1_3_fixed_universe_diagnostic.py", "new_core"),
    ("scripts/external_signal_shadow/run_stage1_3_fixed_universe_diagnostic.py", "new_cli"),
    ("configs/base.py", "reused_config"),
    ("src/risk/limits.py", "reused_safety"),
    ("src/research/external_signal_shadow/models.py", "reused_upstream_models"),
    ("src/research/external_signal_shadow/stage1_3_models.py", "reused_models"),
    ("src/research/external_signal_shadow/stage1_3_candidates.py", "reused_candidates"),
    ("src/research/external_signal_shadow/stage1_3_replay.py", "reused_replay"),
    ("src/research/external_signal_shadow/stage1_3_metrics.py", "reused_metrics"),
)
MAX_HTTP_REQUESTS = 320
MAX_ZIP_BYTES = 256 * 1024 * 1024  # 256 MiB
MIN_REQUEST_INTERVAL_SEC = 1.0
REQUEST_TIMEOUT_SEC = 20.0
MAX_RETRIES_PER_OBJECT = 1
MAX_TOTAL_RETRIES = 20
BUDGET_HOURS_TOTAL_CAP = 8.0
STREAM_CHUNK_SIZE = 65536
CMS_PAGE_SIZE = 50
EXCHANGE_INFO_SPOT_5SYMBOL_URL = (
    "https://api.binance.com/api/v3/exchangeInfo?"
    "symbols=%5B%22BTCUSDT%22%2C%22ETHUSDT%22%2C%22SOLUSDT%22%2C%22XRPUSDT%22%2C%22DOGEUSDT%22%5D"
)

IDENTITY_VERIFICATION_URLS: tuple[dict[str, str], ...] = (
    {
        "id": "exchange_info_spot",
        "url": EXCHANGE_INFO_SPOT_5SYMBOL_URL,
        "purpose": "Current spot symbol status/permissions reference narrowed to fixed 5 symbols",
    },
    {
        "id": "cms_catalog_161_delisting_p1",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=1&pageSize=50",
        "purpose": "Check absence of spot delisting notices (page 1) for fixed 5 symbols in [2026-06-08, 2026-11-23)",
    },
    {
        "id": "cms_catalog_161_delisting_p2",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=2&pageSize=50",
        "purpose": "Check absence of spot delisting notices (page 2 spanning warmup start) in [2026-06-08, 2026-11-23)",
    },
    {
        "id": "cms_catalog_157_maintenance_p1",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=1&pageSize=50",
        "purpose": "Check absence of spot rebrand/merge notices (page 1) for fixed 5 symbols in [2026-06-08, 2026-11-23)",
    },
    {
        "id": "cms_catalog_157_maintenance_p2",
        "url": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=157&pageNo=2&pageSize=50",
        "purpose": "Check absence of spot rebrand/merge notices (page 2 spanning warmup start) in [2026-06-08, 2026-11-23)",
    },
)
ALLOWED_FETCH_HOSTS: frozenset[str] = frozenset(
    {
        "data.binance.vision",
        "api.binance.com",
        "www.binance.com",
    }
)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise DiagnosticStopError("source_manifest_mismatch", f"missing file: {path}")
    return _sha256_bytes(path.read_bytes())


def _write_json_strict(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _require_key(obj: dict[str, Any], key: str, expected_type: type | tuple[type, ...], ctx: str) -> Any:
    if key not in obj:
        raise DiagnosticStopError("source_manifest_mismatch", f"{ctx} missing required key {key!r}")
    val = obj[key]
    if not isinstance(val, expected_type):
        raise DiagnosticStopError(
            "source_manifest_mismatch",
            f"{ctx}.{key} has type {type(val).__name__}, expected {expected_type}",
        )
    if expected_type is str and not val.strip():
        raise DiagnosticStopError("source_manifest_mismatch", f"{ctx}.{key} must be non-empty string")
    return val


def _git_head(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise DiagnosticStopError("source_manifest_mismatch", f"failed to read git HEAD: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _build_symbol_identity_references(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbols": list(protocol["symbols"]),
        "historical_name_origin": {
            "git_commit": "b122dc0700446990b43cc6fe9f613bf76bc8025c",
            "legacy_design_path": "docs/designs/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-design_CN.md",
            "legacy_design_section": "§7",
            "config_constant": "configs/base.py:EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_SYMBOLS",
            "preflight_report_reference": "/Users/tanshuai/crypto-alpha-lab-evidence/2026-11-23-spot-universe-constructability/20261123T082115Z/report_CN_v2.md",
            "preflight_report_sha256": "dca14a1f64df486c094fe332f3871a3ad13755b0c434580228fd4dc2a3dabf92",
        },
        "official_documentation_urls": [
            "https://github.com/binance/binance-public-data",
            "https://data.binance.vision/?prefix=data/spot/monthly/klines/",
        ],
        "required_fetch_identity_checks": list(IDENTITY_VERIFICATION_URLS),
        "qualification_boundary_and_limits": (
            "Current exchangeInfo, archive directory presence, or symbol-name heuristics alone do not prove "
            "continuous historical spot tradability. Task 4 fetch must verify ordinary spot identity and "
            "absence of spot delisting/rebrand events in [2026-06-08T00:00:00Z, 2026-11-23T00:00:00Z); "
            "known egress limitation: api.binance.com/api/v3/exchangeInfo previously returned HTTP 451 "
            "from restricted egress and must fail-closed (STOP=access_restricted) without bypass."
        ),
    }


def _validate_manifest_and_bindings(
    manifest_path: Path,
    *,
    expected_manifest_sha256: str,
) -> tuple[dict[str, Any], Path, Path]:
    actual_manifest_sha = _sha256_file(manifest_path)
    if actual_manifest_sha.lower() != expected_manifest_sha256.lower():
        raise DiagnosticStopError(
            "source_manifest_mismatch",
            f"manifest SHA-256 {actual_manifest_sha} != approved {expected_manifest_sha256}",
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DiagnosticStopError("source_manifest_mismatch", f"invalid manifest JSON: {exc}") from exc

    if not isinstance(manifest, dict):
        raise DiagnosticStopError("source_manifest_mismatch", "manifest root must be JSON object")
    version = _require_key(manifest, "manifest_version", int, "manifest")
    if version != 1:
        raise DiagnosticStopError("source_manifest_mismatch", f"unsupported manifest_version={version}")

    authority = _require_key(manifest, "authority", dict, "manifest")
    repo_root = Path(_require_key(authority, "repo_root", str, "authority")).resolve()
    design_path = _require_key(authority, "design_path", str, "authority")
    design_sha = _require_key(authority, "design_sha256", str, "authority")
    plan_path = _require_key(authority, "plan_path", str, "authority")
    plan_sha = _require_key(authority, "plan_sha256", str, "authority")
    _require_key(authority, "git_head", str, "authority")

    if design_path != DESIGN_REL_PATH or plan_path != PLAN_REL_PATH:
        raise DiagnosticStopError("source_manifest_mismatch", "unexpected design_path or plan_path")
    if _sha256_file(repo_root / design_path).lower() != design_sha.lower():
        raise DiagnosticStopError("source_manifest_mismatch", "bound Design SHA-256 mismatch on disk")
    if _sha256_file(repo_root / plan_path).lower() != plan_sha.lower():
        raise DiagnosticStopError("source_manifest_mismatch", "bound Plan SHA-256 mismatch on disk")

    verify_base_and_safety_config()
    protocol = _require_key(manifest, "protocol", dict, "manifest")
    validate_protocol(protocol)

    resources = _require_key(manifest, "resources", dict, "manifest")
    if (
        _require_key(resources, "max_http_requests", int, "resources") != MAX_HTTP_REQUESTS
        or _require_key(resources, "max_zip_bytes", int, "resources") != MAX_ZIP_BYTES
        or _require_key(resources, "min_request_interval_sec", (int, float), "resources") < MIN_REQUEST_INTERVAL_SEC
        or _require_key(resources, "request_timeout_sec", (int, float), "resources") > REQUEST_TIMEOUT_SEC
        or _require_key(resources, "max_retries_per_object", int, "resources") != MAX_RETRIES_PER_OBJECT
        or _require_key(resources, "max_total_retries", int, "resources") != MAX_TOTAL_RETRIES
    ):
        raise DiagnosticStopError("source_manifest_mismatch", "manifest resources violate frozen limits")

    output_cfg = _require_key(manifest, "output", dict, "manifest")
    run_root = Path(_require_key(output_cfg, "run_root", str, "output"))

    bindings = _require_key(manifest, "source_bindings", list, "manifest")
    expected_binding_paths = [p for p, _ in SOURCE_BINDING_SPECS]
    actual_binding_paths = []
    for item in bindings:
        if not isinstance(item, dict):
            raise DiagnosticStopError("source_manifest_mismatch", "source_binding entry must be object")
        rel_p = _require_key(item, "path", str, "source_binding")
        exp_sha = _require_key(item, "sha256", str, "source_binding")
        _require_key(item, "role", str, "source_binding")
        actual_binding_paths.append(rel_p)
        disk_sha = _sha256_file(repo_root / rel_p)
        if disk_sha.lower() != exp_sha.lower():
            raise DiagnosticStopError(
                "source_identity_mismatch",
                f"source binding {rel_p} SHA-256 {disk_sha} != manifest {exp_sha}",
            )
    if actual_binding_paths != expected_binding_paths:
        raise DiagnosticStopError("source_identity_mismatch", "source_bindings path list mismatch")

    sym_id_refs = _require_key(manifest, "symbol_identity_references", dict, "manifest")
    req_id_checks = _require_key(
        sym_id_refs,
        "required_fetch_identity_checks",
        list,
        "symbol_identity_references",
    )
    if req_id_checks != list(IDENTITY_VERIFICATION_URLS):
        raise DiagnosticStopError(
            "source_manifest_mismatch",
            "required_fetch_identity_checks mismatch against frozen IDENTITY_VERIFICATION_URLS",
        )

    archive_objects = _require_key(manifest, "archive_objects", list, "manifest")
    expected_objects = build_expected_archive_objects(protocol)
    if archive_objects != expected_objects:
        raise DiagnosticStopError(
            "source_manifest_mismatch",
            f"archive_objects mismatch: expected exact {len(expected_objects)} frozen objects",
        )

    return manifest, repo_root, run_root


def _default_http_transport(url: str, timeout: float) -> Any:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_FETCH_HOSTS:
        raise DiagnosticStopError("source_manifest_mismatch", f"disallowed fetch URL: {url}")
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CryptoAlphaLabStage13Diagnostic/1.0)",
            "Accept": "*/*",
        },
    )
    ssl_ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(
        _NoRedirectHandler(),
        urllib.request.HTTPSHandler(context=ssl_ctx),
    )
    return opener.open(req, timeout=timeout)


class _BoundedFetcher:
    """Enforces 320-request cap, 256 MiB streaming ZIP cap, >=1s serial spacing, and bounded TLS retries."""

    def __init__(
        self,
        *,
        run_root: Path,
        max_requests: int,
        max_zip_bytes: int,
        min_interval_sec: float,
        timeout_sec: float,
        max_retries_per_object: int,
        max_total_retries: int,
        transport: Callable[[str, float], Any],
        sleep_fn: Callable[[float], None],
    ) -> None:
        self.run_root = run_root
        self.max_requests = max_requests
        self.max_zip_bytes = max_zip_bytes
        self.min_interval_sec = min_interval_sec
        self.timeout_sec = timeout_sec
        self.max_retries_per_object = max_retries_per_object
        self.max_total_retries = max_total_retries
        self.transport = transport
        self.sleep_fn = sleep_fn
        self.requests_used = 0
        self.retries_used = 0
        self.zip_bytes_received = 0
        self.request_log_path = run_root / "logs" / "http_requests.jsonl"
        self.failed_attempts_dir = run_root / "raw" / "failed_attempts"

    def _log_request(self, record: dict[str, Any]) -> None:
        self.request_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.request_log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")

    def _is_retryable_network_exc(self, exc: Exception) -> bool:
        if isinstance(exc, (ssl.SSLError, TimeoutError, socket.timeout)):
            return True
        if isinstance(exc, urllib.error.URLError):
            reason = exc.reason
            if isinstance(reason, (ssl.SSLError, TimeoutError, socket.timeout)):
                return True
        return False

    def _record_network_failure(
        self,
        *,
        req_id: int,
        started_utc: str,
        object_tag: str,
        attempt: int,
        url: str,
        status_code: int | None,
        is_zip: bool,
        bytes_received: int,
        exc: Exception,
    ) -> None:
        self.failed_attempts_dir.mkdir(parents=True, exist_ok=True)
        fail_record_path = self.failed_attempts_dir / f"req_{req_id:04d}_{object_tag}_attempt_{attempt}.json"
        _write_json_strict(
            fail_record_path,
            {
                "request_id": req_id,
                "started_utc": started_utc,
                "finished_utc": _utc_now(),
                "object_tag": object_tag,
                "attempt": attempt,
                "url": url,
                "status_code": status_code,
                "is_zip": is_zip,
                "bytes_received": bytes_received,
                "cumulative_requests": self.requests_used,
                "cumulative_zip_bytes": self.zip_bytes_received,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        self._log_request(
            {
                "request_id": req_id,
                "started_utc": started_utc,
                "finished_utc": _utc_now(),
                "object_tag": object_tag,
                "attempt": attempt,
                "url": url,
                "status_code": status_code,
                "is_zip": is_zip,
                "bytes_received": bytes_received,
                "sha256": None,
                "cumulative_requests": self.requests_used,
                "cumulative_zip_bytes": self.zip_bytes_received,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )

    def fetch_bytes(
        self,
        *,
        object_tag: str,
        url: str,
        is_zip: bool,
    ) -> tuple[bytes, dict[str, Any]]:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_FETCH_HOSTS:
            raise DiagnosticStopError("source_manifest_mismatch", f"disallowed URL: {url}")

        attempt = 0
        while True:
            if attempt > 0:
                if attempt > self.max_retries_per_object:
                    raise DiagnosticStopError(
                        "coverage_incomplete",
                        f"exceeded max_retries_per_object={self.max_retries_per_object} for {object_tag}",
                    )
                if self.retries_used >= self.max_total_retries:
                    raise DiagnosticStopError(
                        "request_limit",
                        f"exceeded max_total_retries={self.max_total_retries}",
                    )
                self.retries_used += 1

            # Check request cap BEFORE making request #321
            if self.requests_used >= self.max_requests:
                raise DiagnosticStopError(
                    "request_limit",
                    f"max_http_requests={self.max_requests} reached before requesting {url}",
                )

            if self.requests_used > 0:
                self.sleep_fn(self.min_interval_sec)

            self.requests_used += 1
            req_id = self.requests_used
            started_utc = _utc_now()
            attempt += 1

            try:
                resp = self.transport(url, self.timeout_sec)
            except urllib.error.HTTPError as exc:
                code = int(exc.code)
                self._log_request(
                    {
                        "request_id": req_id,
                        "started_utc": started_utc,
                        "finished_utc": _utc_now(),
                        "object_tag": object_tag,
                        "attempt": attempt,
                        "url": url,
                        "status_code": code,
                        "is_zip": is_zip,
                        "bytes_received": 0,
                        "cumulative_requests": self.requests_used,
                        "cumulative_zip_bytes": self.zip_bytes_received,
                        "error": f"HTTPError {code}",
                    }
                )
                if code in (403, 429, 451):
                    raise DiagnosticStopError("access_restricted", f"HTTP {code} on {url}") from exc
                raise DiagnosticStopError("coverage_incomplete", f"HTTP {code} on {url}") from exc
            except Exception as exc:
                self._record_network_failure(
                    req_id=req_id,
                    started_utc=started_utc,
                    object_tag=object_tag,
                    attempt=attempt,
                    url=url,
                    status_code=None,
                    is_zip=is_zip,
                    bytes_received=0,
                    exc=exc,
                )
                if self._is_retryable_network_exc(exc) and attempt <= self.max_retries_per_object:
                    continue
                raise DiagnosticStopError(
                    "coverage_incomplete",
                    f"network error on {url}: {type(exc).__name__}: {exc}",
                ) from exc

            status = int(resp.status)
            if status in (403, 429, 451):
                self._log_request(
                    {
                        "request_id": req_id,
                        "started_utc": started_utc,
                        "finished_utc": _utc_now(),
                        "object_tag": object_tag,
                        "attempt": attempt,
                        "url": url,
                        "status_code": status,
                        "is_zip": is_zip,
                        "bytes_received": 0,
                        "cumulative_requests": self.requests_used,
                        "cumulative_zip_bytes": self.zip_bytes_received,
                        "error": f"HTTP {status}",
                    }
                )
                raise DiagnosticStopError("access_restricted", f"HTTP {status} on {url}")
            if status != 200:
                self._log_request(
                    {
                        "request_id": req_id,
                        "started_utc": started_utc,
                        "finished_utc": _utc_now(),
                        "object_tag": object_tag,
                        "attempt": attempt,
                        "url": url,
                        "status_code": status,
                        "is_zip": is_zip,
                        "bytes_received": 0,
                        "cumulative_requests": self.requests_used,
                        "cumulative_zip_bytes": self.zip_bytes_received,
                        "error": f"HTTP {status}",
                    }
                )
                raise DiagnosticStopError("coverage_incomplete", f"unexpected HTTP {status} on {url}")

            # Streaming read with strict remaining ZIP byte cap (never read past remaining cap)
            content_length_int: int | None = None
            raw_headers = getattr(resp, "headers", None)
            if raw_headers is not None:
                cl_raw = None
                if hasattr(raw_headers, "get"):
                    cl_raw = raw_headers.get("Content-Length") or raw_headers.get("content-length")
                if isinstance(cl_raw, str) and cl_raw.strip().isdigit():
                    content_length_int = int(cl_raw.strip())

            def _log_byte_limit_failure(received_now: int, detail: str) -> None:
                self._log_request(
                    {
                        "request_id": req_id,
                        "started_utc": started_utc,
                        "finished_utc": _utc_now(),
                        "object_tag": object_tag,
                        "attempt": attempt,
                        "url": url,
                        "status_code": status,
                        "is_zip": is_zip,
                        "bytes_received": received_now,
                        "sha256": None,
                        "cumulative_requests": self.requests_used,
                        "cumulative_zip_bytes": self.zip_bytes_received,
                        "error": f"STOP=download_byte_limit: {detail}",
                    }
                )

            buf = bytearray()
            bytes_read = 0
            stream_retry = False
            try:
                if is_zip and content_length_int is not None:
                    remaining_before = self.max_zip_bytes - self.zip_bytes_received
                    if content_length_int > remaining_before:
                        detail = (
                            f"Content-Length {content_length_int} exceeds remaining ZIP budget "
                            f"{remaining_before} on {url}"
                        )
                        _log_byte_limit_failure(0, detail)
                        raise DiagnosticStopError("download_byte_limit", detail)

                while True:
                    if is_zip:
                        remaining = self.max_zip_bytes - self.zip_bytes_received
                        if remaining <= 0:
                            detail = f"cumulative ZIP bytes reached {self.max_zip_bytes} before reading {url}"
                            _log_byte_limit_failure(bytes_read, detail)
                            raise DiagnosticStopError("download_byte_limit", detail)
                        to_read = min(STREAM_CHUNK_SIZE, remaining)
                    else:
                        to_read = STREAM_CHUNK_SIZE
                    chunk = resp.read(to_read)
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    if is_zip:
                        self.zip_bytes_received += len(chunk)
                        if self.zip_bytes_received > self.max_zip_bytes:
                            detail = f"received ZIP bytes {self.zip_bytes_received} exceeded cap {self.max_zip_bytes} on {url}"
                            _log_byte_limit_failure(bytes_read, detail)
                            raise DiagnosticStopError("download_byte_limit", detail)
                    buf.extend(chunk)
                    if is_zip and self.zip_bytes_received == self.max_zip_bytes:
                        if content_length_int is not None and bytes_read == content_length_int:
                            break
                        detail = (
                            f"cumulative ZIP bytes hit cap {self.max_zip_bytes} without confirmed EOF on {url}"
                        )
                        _log_byte_limit_failure(bytes_read, detail)
                        raise DiagnosticStopError("download_byte_limit", detail)
            except DiagnosticStopError:
                raise
            except Exception as exc:
                self._record_network_failure(
                    req_id=req_id,
                    started_utc=started_utc,
                    object_tag=object_tag,
                    attempt=attempt,
                    url=url,
                    status_code=status,
                    is_zip=is_zip,
                    bytes_received=bytes_read,
                    exc=exc,
                )
                if self._is_retryable_network_exc(exc) and attempt <= self.max_retries_per_object:
                    stream_retry = True
                else:
                    raise DiagnosticStopError(
                        "coverage_incomplete",
                        f"stream error on {url}: {type(exc).__name__}: {exc}",
                    ) from exc
            finally:
                close_fn = getattr(resp, "close", None)
                if callable(close_fn):
                    close_fn()

            if stream_retry:
                continue

            data = bytes(buf)
            rec = {
                "request_id": req_id,
                "started_utc": started_utc,
                "finished_utc": _utc_now(),
                "object_tag": object_tag,
                "attempt": attempt,
                "url": url,
                "status_code": status,
                "is_zip": is_zip,
                "bytes_received": bytes_read,
                "sha256": _sha256_bytes(data),
                "cumulative_requests": self.requests_used,
                "cumulative_zip_bytes": self.zip_bytes_received,
                "error": None,
            }
            self._log_request(rec)
            return data, rec


def _cmd_prepare(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    run_root = Path(args.run_root)
    output_path = Path(args.output)

    if run_root.exists():
        raise DiagnosticStopError("existing_output_root", f"run_root already exists: {run_root}")
    if output_path.exists():
        raise DiagnosticStopError("existing_output_root", f"manifest output already exists: {output_path}")

    verify_base_and_safety_config()
    protocol = build_default_protocol()

    design_actual_sha = _sha256_file(repo_root / DESIGN_REL_PATH)
    if design_actual_sha.lower() != args.design_sha256.lower():
        raise DiagnosticStopError(
            "source_manifest_mismatch",
            f"Design SHA-256 {design_actual_sha} != --design-sha256 {args.design_sha256}",
        )
    plan_actual_sha = _sha256_file(repo_root / PLAN_REL_PATH)
    if plan_actual_sha.lower() != args.plan_sha256.lower():
        raise DiagnosticStopError(
            "source_manifest_mismatch",
            f"Plan SHA-256 {plan_actual_sha} != --plan-sha256 {args.plan_sha256}",
        )

    source_bindings = [
        {
            "path": rel_path,
            "sha256": _sha256_file(repo_root / rel_path),
            "role": role,
        }
        for rel_path, role in SOURCE_BINDING_SPECS
    ]

    archive_objects = build_expected_archive_objects(protocol)
    manifest = {
        "manifest_version": 1,
        "generated_at_utc": _utc_now(),
        "authority": {
            "repo_root": str(repo_root),
            "design_path": DESIGN_REL_PATH,
            "design_sha256": design_actual_sha,
            "plan_path": PLAN_REL_PATH,
            "plan_sha256": plan_actual_sha,
            "git_head": _git_head(repo_root),
        },
        "source_bindings": source_bindings,
        "protocol": protocol,
        "resources": {
            "max_http_requests": MAX_HTTP_REQUESTS,
            "max_zip_bytes": MAX_ZIP_BYTES,
            "min_request_interval_sec": MIN_REQUEST_INTERVAL_SEC,
            "request_timeout_sec": REQUEST_TIMEOUT_SEC,
            "max_retries_per_object": MAX_RETRIES_PER_OBJECT,
            "max_total_retries": MAX_TOTAL_RETRIES,
            "budget_hours_total_cap": BUDGET_HOURS_TOTAL_CAP,
        },
        "output": {
            "run_root": str(run_root),
        },
        "symbol_identity_references": _build_symbol_identity_references(protocol),
        "archive_objects": archive_objects,
    }
    _write_json_strict(output_path, manifest)
    # Self-validate manifest via shared consumer validator
    manifest_sha = _sha256_file(output_path)
    _validate_manifest_and_bindings(output_path, expected_manifest_sha256=manifest_sha)
    print(f"PREPARED_MANIFEST={output_path} SHA256={manifest_sha}")
    return 0


def _resolve_confined_expected_path(
    run_root: Path,
    *,
    recorded_rel: Any,
    expected_rel: Path,
    label: str,
) -> Path:
    """Strictly confine an input path to its predetermined location inside run_root (no abs/traversal/symlink)."""
    if not isinstance(recorded_rel, str) or not recorded_rel.strip():
        raise DiagnosticStopError("source_identity_mismatch", f"{label} path must be non-empty relative string")
    rec_path = Path(recorded_rel)
    if rec_path.is_absolute() or ".." in rec_path.parts or rec_path != expected_rel:
        raise DiagnosticStopError(
            "source_identity_mismatch",
            f"{label} recorded path {recorded_rel!r} != expected confined path {str(expected_rel)!r}",
        )
    resolved_root = run_root.resolve()
    cur = run_root
    for part in expected_rel.parts:
        cur = cur / part
        if cur.is_symlink():
            raise DiagnosticStopError("source_identity_mismatch", f"{label} symlink rejected: {cur}")
    if not cur.is_file():
        raise DiagnosticStopError("coverage_incomplete", f"{label} missing file: {cur}")
    resolved_target = cur.resolve()
    if not resolved_target.is_relative_to(resolved_root) or resolved_target != (resolved_root / expected_rel):
        raise DiagnosticStopError(
            "source_identity_mismatch",
            f"{label} resolved path {resolved_target} escaped run_root {resolved_root}",
        )
    return cur


def _verify_identity_payloads(
    identity_bytes: dict[str, bytes],
    *,
    symbols: list[str],
    warmup_start_ms: int,
    eval_end_ms: int,
) -> dict[str, Any]:
    required_keys = (
        "exchange_info_spot",
        "cms_catalog_161_delisting_p1",
        "cms_catalog_161_delisting_p2",
        "cms_catalog_157_maintenance_p1",
        "cms_catalog_157_maintenance_p2",
    )
    for k in required_keys:
        if k not in identity_bytes:
            raise DiagnosticStopError("coverage_incomplete", f"missing required identity payload {k!r}")

    try:
        exch = json.loads(identity_bytes["exchange_info_spot"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DiagnosticStopError("coverage_incomplete", f"invalid exchangeInfo JSON: {exc}") from exc

    if not isinstance(exch, dict) or not isinstance(exch.get("symbols"), list) or not exch["symbols"]:
        raise DiagnosticStopError("coverage_incomplete", "exchangeInfo missing non-empty symbols list")
    sym_map = {item["symbol"]: item for item in exch["symbols"] if isinstance(item, dict) and "symbol" in item}
    if len(exch["symbols"]) != len(symbols) or set(sym_map.keys()) != set(symbols):
        raise DiagnosticStopError(
            "coverage_incomplete",
            "exchangeInfo symbol set mismatch against fixed 5-symbol query",
        )
    symbol_checks: dict[str, Any] = {}
    for sym in symbols:
        info = sym_map[sym]
        perms: set[str] = set()
        if "permissions" in info and isinstance(info["permissions"], list):
            perms.update(str(p) for p in info["permissions"])
        if "permissionSets" in info and isinstance(info["permissionSets"], list):
            for pset in info["permissionSets"]:
                if isinstance(pset, list):
                    perms.update(str(p) for p in pset)
        if (
            info.get("status") != "TRADING"
            or info.get("baseAsset") != sym[:-4]
            or info.get("quoteAsset") != "USDT"
            or info.get("isSpotTradingAllowed") is not True
            or (perms and "SPOT" not in perms)
        ):
            raise DiagnosticStopError("coverage_incomplete", f"{sym} failed spot identity check in exchangeInfo")
        symbol_checks[sym] = {
            "exchange_info_status": info["status"],
            "base_asset": info["baseAsset"],
            "quote_asset": info["quoteAsset"],
            "is_spot_trading_allowed": info["isSpotTradingAllowed"],
        }

    # Validate CMS catalog fixed-page completeness & temporal span across [warmup_start_ms, eval_end_ms)
    target_symbols = {sym.upper() for sym in symbols}
    base_assets = {sym[:-4].upper() for sym in symbols}
    match_targets = target_symbols | base_assets
    lifecycle_flags: list[dict[str, Any]] = []
    catalog_coverage: dict[str, Any] = {}

    catalog_specs = (
        (
            "catalog_161_delisting",
            161,
            ("cms_catalog_161_delisting_p1", "cms_catalog_161_delisting_p2"),
        ),
        (
            "catalog_157_maintenance",
            157,
            ("cms_catalog_157_maintenance_p1", "cms_catalog_157_maintenance_p2"),
        ),
    )
    for cat_label, expected_cat_id, page_keys in catalog_specs:
        seen_codes: set[str] = set()
        collected_articles: list[dict[str, Any]] = []
        reported_totals: list[int] = []
        prev_page_oldest_ms: int | None = None

        for page_idx, pkey in enumerate(page_keys):
            try:
                cms = json.loads(identity_bytes[pkey].decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DiagnosticStopError("coverage_incomplete", f"invalid CMS JSON in {pkey}: {exc}") from exc
            if (
                not isinstance(cms, dict)
                or cms.get("code") != "000000"
                or cms.get("success") is not True
                or not isinstance(cms.get("data"), dict)
                or not isinstance(cms["data"].get("catalogs"), list)
                or not cms["data"]["catalogs"]
            ):
                raise DiagnosticStopError("coverage_incomplete", f"CMS payload envelope invalid in {pkey}")
            cat_obj = cms["data"]["catalogs"][0]
            if not isinstance(cat_obj, dict):
                raise DiagnosticStopError("coverage_incomplete", f"CMS catalog entry invalid in {pkey}")
            if "catalogId" in cat_obj and int(cat_obj["catalogId"]) != expected_cat_id:
                raise DiagnosticStopError(
                    "coverage_incomplete",
                    f"CMS catalogId mismatch in {pkey}: got {cat_obj['catalogId']}, expected {expected_cat_id}",
                )
            total_raw = cat_obj.get("total")
            if isinstance(total_raw, bool) or not isinstance(total_raw, int) or total_raw < 1:
                raise DiagnosticStopError(
                    "coverage_incomplete",
                    f"CMS {pkey} missing valid positive integer total: {total_raw!r}",
                )
            reported_totals.append(total_raw)
            arts = cat_obj.get("articles")
            if not isinstance(arts, list):
                raise DiagnosticStopError("coverage_incomplete", f"CMS {pkey} articles must be list")

            # Fixed-page pagination completeness: each page must contain exact expected count for pageSize=50
            remaining_from_page = max(0, total_raw - page_idx * CMS_PAGE_SIZE)
            expected_page_count = min(CMS_PAGE_SIZE, remaining_from_page)
            if len(arts) != expected_page_count:
                raise DiagnosticStopError(
                    "coverage_incomplete",
                    f"CMS {pkey} page {page_idx + 1} returned {len(arts)} articles, "
                    f"expected {expected_page_count} (pageSize={CMS_PAGE_SIZE}, total={total_raw})",
                )

            page_seen: set[str] = set()
            page_dates: list[int] = []
            for art in arts:
                if (
                    not isinstance(art, dict)
                    or isinstance(art.get("releaseDate"), bool)
                    or not isinstance(art.get("releaseDate"), int)
                    or not isinstance(art.get("title"), str)
                    or not art["title"].strip()
                ):
                    raise DiagnosticStopError("coverage_incomplete", f"malformed CMS article in {pkey}")
                art_key = str(art["code"]) if "code" in art else f"{art['releaseDate']}:{art['title']}"
                if art_key in page_seen:
                    raise DiagnosticStopError(
                        "coverage_incomplete",
                        f"CMS {pkey} contains duplicate article key {art_key!r}",
                    )
                page_seen.add(art_key)
                rel_ms = int(art["releaseDate"])
                if page_dates and rel_ms > page_dates[-1]:
                    raise DiagnosticStopError(
                        "coverage_incomplete",
                        f"CMS {pkey} articles not in descending releaseDate order",
                    )
                page_dates.append(rel_ms)
                if art_key not in seen_codes:
                    seen_codes.add(art_key)
                    collected_articles.append(art)

            if page_dates:
                if prev_page_oldest_ms is not None and page_dates[0] > prev_page_oldest_ms:
                    raise DiagnosticStopError(
                        "coverage_incomplete",
                        f"CMS {pkey} page {page_idx + 1} newest releaseDate {page_dates[0]} "
                        f"exceeds previous page oldest {prev_page_oldest_ms}",
                    )
                prev_page_oldest_ms = page_dates[-1]

        if len(set(reported_totals)) != 1:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"CMS {cat_label} reported total changed across pages: {reported_totals}",
            )
        catalog_total = reported_totals[0]
        expected_unique = min(catalog_total, len(page_keys) * CMS_PAGE_SIZE)
        if not collected_articles or len(collected_articles) != expected_unique:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"CMS {cat_label} unique article count {len(collected_articles)} != expected "
                f"{expected_unique} (total={catalog_total}, pages={len(page_keys)})",
            )
        release_dates = [int(a["releaseDate"]) for a in collected_articles]
        oldest_ms = min(release_dates)
        newest_ms = max(release_dates)
        full_catalog_fetched = len(collected_articles) >= catalog_total
        spans_warmup_boundary = full_catalog_fetched or (oldest_ms <= warmup_start_ms)
        if not spans_warmup_boundary:
            raise DiagnosticStopError(
                "coverage_incomplete",
                f"CMS {cat_label} pagination incomplete: collected={len(collected_articles)}/{catalog_total}, "
                f"oldest_release_ms={oldest_ms} > warmup_start_ms={warmup_start_ms}",
            )

        for art in collected_articles:
            rel_ms = int(art["releaseDate"])
            if not (warmup_start_ms <= rel_ms < eval_end_ms):
                continue
            title = str(art["title"])
            title_l = title.lower()
            if any(
                k in title_l
                for k in ("delist", "rebrand", "token merge", "token swap", "removal of spot", "cease trading")
            ):
                tokens = set(re.findall(r"[A-Za-z0-9]+", title.upper()))
                hit = sorted(match_targets & tokens)
                if hit:
                    lifecycle_flags.append({"source": cat_label, "title": title, "hit_targets": hit})

        catalog_coverage[cat_label] = {
            "reported_total": catalog_total,
            "articles_collected": len(collected_articles),
            "oldest_release_ms": oldest_ms,
            "newest_release_ms": newest_ms,
            "full_catalog_fetched": full_catalog_fetched,
            "spans_warmup_boundary": spans_warmup_boundary,
        }

    if lifecycle_flags:
        raise DiagnosticStopError(
            "coverage_incomplete",
            f"potential lifecycle delisting/rebrand detected for fixed symbols: {lifecycle_flags}",
        )

    return {
        "symbol_checks": symbol_checks,
        "catalog_coverage": catalog_coverage,
        "lifecycle_conflicts": lifecycle_flags,
        "identity_checks_passed": True,
    }


def _cmd_fetch(
    args: argparse.Namespace,
    *,
    http_transport: Callable[[str, float], Any] | None,
    sleep_fn: Callable[[float], None] | None,
) -> int:
    manifest_path = Path(args.manifest)
    manifest, _repo_root, run_root = _validate_manifest_and_bindings(
        manifest_path, expected_manifest_sha256=args.manifest_sha256
    )
    if run_root.exists():
        raise DiagnosticStopError("existing_output_root", f"run_root already exists: {run_root}")

    run_root.mkdir(parents=True, exist_ok=False)
    (run_root / "raw" / "identity").mkdir(parents=True, exist_ok=True)
    (run_root / "raw" / "archives").mkdir(parents=True, exist_ok=True)
    (run_root / "logs").mkdir(parents=True, exist_ok=True)

    resources = manifest["resources"]
    fetcher = _BoundedFetcher(
        run_root=run_root,
        max_requests=int(resources["max_http_requests"]),
        max_zip_bytes=int(resources["max_zip_bytes"]),
        min_interval_sec=float(resources["min_request_interval_sec"]),
        timeout_sec=float(resources["request_timeout_sec"]),
        max_retries_per_object=int(resources["max_retries_per_object"]),
        max_total_retries=int(resources["max_total_retries"]),
        transport=http_transport if http_transport is not None else _default_http_transport,
        sleep_fn=sleep_fn if sleep_fn is not None else time.sleep,
    )

    protocol = manifest["protocol"]
    identity_records: list[dict[str, Any]] = []
    archive_records: list[dict[str, Any]] = []

    try:
        # 1. Fetch & verify symbol identity / lifecycle references
        identity_bytes: dict[str, bytes] = {}
        for item in manifest["symbol_identity_references"]["required_fetch_identity_checks"]:
            raw_b, rec = fetcher.fetch_bytes(
                object_tag=f"id_{item['id']}",
                url=item["url"],
                is_zip=False,
            )
            rel_out = Path("raw") / "identity" / f"{item['id']}.json"
            (run_root / rel_out).write_bytes(raw_b)
            identity_bytes[item["id"]] = raw_b
            identity_records.append(
                {
                    "id": item["id"],
                    "url": item["url"],
                    "relative_path": str(rel_out),
                    "sha256": rec["sha256"],
                    "bytes": rec["bytes_received"],
                    "fetched_utc": rec["finished_utc"],
                }
            )
        identity_summary = _verify_identity_payloads(
            identity_bytes,
            symbols=protocol["symbols"],
            warmup_start_ms=int(protocol["warmup_start_ms"]),
            eval_end_ms=int(protocol["eval_end_ms"]),
        )

        # 2. Fetch and strictly validate all 135 archive objects
        all_bars: list[HistoricalBar] = []
        for obj in manifest["archive_objects"]:
            zip_bytes, zip_rec = fetcher.fetch_bytes(
                object_tag=obj["zip_filename"],
                url=obj["zip_url"],
                is_zip=True,
            )
            chk_bytes, chk_rec = fetcher.fetch_bytes(
                object_tag=obj["checksum_filename"],
                url=obj["checksum_url"],
                is_zip=False,
            )
            zip_rel = Path("raw") / "archives" / obj["zip_filename"]
            chk_rel = Path("raw") / "archives" / obj["checksum_filename"]
            (run_root / zip_rel).write_bytes(zip_bytes)
            (run_root / chk_rel).write_bytes(chk_bytes)

            parsed_bars, meta = parse_kline_zip_bytes(
                zip_bytes,
                checksum_text=chk_bytes.decode("utf-8"),
                expected_zip_filename=obj["zip_filename"],
                expected_csv_filename=obj["csv_filename"],
                expected_symbol=obj["symbol"],
                expected_utc_dates=obj["expected_utc_dates"],
            )
            all_bars.extend(parsed_bars)
            archive_records.append(
                {
                    "object_id": obj["object_id"],
                    "symbol": obj["symbol"],
                    "granularity": obj["granularity"],
                    "period": obj["period"],
                    "zip_relative_path": str(zip_rel),
                    "checksum_relative_path": str(chk_rel),
                    "zip_sha256": zip_rec["sha256"],
                    "checksum_sha256": chk_rec["sha256"],
                    "zip_bytes": zip_rec["bytes_received"],
                    "row_count": meta["row_count"],
                    "first_bar_start_ms": meta["first_bar_start_ms"],
                    "last_bar_end_ms": meta["last_bar_end_ms"],
                    "zero_quote_volume_bar_count": meta["zero_quote_volume_bar_count"],
                    "fetched_utc": zip_rec["finished_utc"],
                }
            )

        # 3. Verify complete 168-day [warmup, eval_end) grid across all 5 symbols
        from research.external_signal_shadow.stage1_3_fixed_universe_diagnostic import (
            _validate_and_index_bars,
        )

        grouped, excluded_outside = _validate_and_index_bars(all_bars, protocol)
        coverage_payload = {
            "coverage_qualified": True,
            "stop_code": None,
            "manifest_sha256": args.manifest_sha256.lower(),
            "generated_at_utc": _utc_now(),
            "total_archive_objects": len(archive_records),
            "http_requests_used": fetcher.requests_used,
            "http_retries_used": fetcher.retries_used,
            "cumulative_zip_bytes": fetcher.zip_bytes_received,
            "identity_verification": identity_summary,
            "identity_files": identity_records,
            "bars_in_study_range_by_symbol": {sym: len(grouped[sym]) for sym in protocol["symbols"]},
            "excluded_outside_study_range_by_symbol": excluded_outside,
            "archive_records": archive_records,
        }
        _write_json_strict(run_root / "coverage.json", coverage_payload)
        print(f"FETCH_COVERAGE_QUALIFIED=true RUN_ROOT={run_root}")
        return 0
    except DiagnosticStopError as exc:
        _write_json_strict(
            run_root / "coverage.json",
            {
                "coverage_qualified": False,
                "stop_code": exc.stop_code,
                "detail": exc.detail,
                "manifest_sha256": args.manifest_sha256.lower(),
                "generated_at_utc": _utc_now(),
                "http_requests_used": fetcher.requests_used,
                "http_retries_used": fetcher.retries_used,
                "cumulative_zip_bytes": fetcher.zip_bytes_received,
                "archive_records_completed": len(archive_records),
            },
        )
        raise


def _cmd_analyze(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest, _repo_root, run_root = _validate_manifest_and_bindings(
        manifest_path, expected_manifest_sha256=args.manifest_sha256
    )

    coverage_path = run_root / "coverage.json"
    if coverage_path.is_symlink():
        raise DiagnosticStopError("source_identity_mismatch", f"coverage.json symlink rejected: {coverage_path}")
    if not coverage_path.is_file():
        raise DiagnosticStopError("coverage_incomplete", f"missing coverage.json in {run_root}")
    results_dir = run_root / "results"
    if results_dir.exists():
        raise DiagnosticStopError("existing_output_root", f"results directory already exists: {results_dir}")

    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    if coverage["coverage_qualified"] is not True:
        raise DiagnosticStopError("coverage_incomplete", "coverage.json is not qualified")
    if coverage["manifest_sha256"].lower() != args.manifest_sha256.lower():
        raise DiagnosticStopError("source_manifest_mismatch", "coverage.json manifest_sha256 mismatch")

    # Re-verify ALL required identity raw files (confined path, existence, digest, semantics, immutability)
    required_id_checks = manifest["symbol_identity_references"]["required_fetch_identity_checks"]
    if "identity_files" not in coverage or not isinstance(coverage["identity_files"], list):
        raise DiagnosticStopError("coverage_incomplete", "coverage.json missing identity_files list")
    id_rec_by_id = {rec["id"]: rec for rec in coverage["identity_files"] if isinstance(rec, dict) and "id" in rec}
    expected_id_keys = [item["id"] for item in required_id_checks]
    if len(id_rec_by_id) != len(expected_id_keys) or set(id_rec_by_id.keys()) != set(expected_id_keys):
        raise DiagnosticStopError("coverage_incomplete", "coverage.json identity_files set mismatch")

    pre_digests: list[tuple[Path, str]] = []
    identity_bytes: dict[str, bytes] = {}
    for item in required_id_checks:
        id_key = item["id"]
        id_rec = id_rec_by_id[id_key]
        expected_id_rel = Path("raw") / "identity" / f"{id_key}.json"
        id_path = _resolve_confined_expected_path(
            run_root,
            recorded_rel=id_rec["relative_path"],
            expected_rel=expected_id_rel,
            label=f"identity:{id_key}",
        )
        raw_id_bytes = id_path.read_bytes()
        id_sha = _sha256_bytes(raw_id_bytes)
        if id_sha.lower() != str(id_rec["sha256"]).lower():
            raise DiagnosticStopError(
                "checksum_mismatch",
                f"identity raw file digest mismatch vs coverage.json for {id_key}",
            )
        identity_bytes[id_key] = raw_id_bytes
        pre_digests.append((id_path, id_sha))

    _verify_identity_payloads(
        identity_bytes,
        symbols=manifest["protocol"]["symbols"],
        warmup_start_ms=int(manifest["protocol"]["warmup_start_ms"]),
        eval_end_ms=int(manifest["protocol"]["eval_end_ms"]),
    )

    cov_by_id = {rec["object_id"]: rec for rec in coverage["archive_records"]}
    if len(cov_by_id) != len(manifest["archive_objects"]):
        raise DiagnosticStopError("coverage_incomplete", "coverage archive_records count mismatch")

    # Re-verify every ZIP and CHECKSUM confined inside run_root (pre-read AND post-read)
    all_bars: list[HistoricalBar] = []
    for obj in manifest["archive_objects"]:
        oid = obj["object_id"]
        if oid not in cov_by_id:
            raise DiagnosticStopError("coverage_incomplete", f"missing coverage record for {oid}")
        rec = cov_by_id[oid]
        expected_zip_rel = Path("raw") / "archives" / obj["zip_filename"]
        expected_chk_rel = Path("raw") / "archives" / obj["checksum_filename"]
        zip_path = _resolve_confined_expected_path(
            run_root,
            recorded_rel=rec["zip_relative_path"],
            expected_rel=expected_zip_rel,
            label=f"archive_zip:{oid}",
        )
        chk_path = _resolve_confined_expected_path(
            run_root,
            recorded_rel=rec["checksum_relative_path"],
            expected_rel=expected_chk_rel,
            label=f"archive_checksum:{oid}",
        )

        zip_bytes = zip_path.read_bytes()
        chk_bytes = chk_path.read_bytes()
        zip_sha = _sha256_bytes(zip_bytes)
        chk_sha = _sha256_bytes(chk_bytes)
        if zip_sha.lower() != rec["zip_sha256"].lower() or chk_sha.lower() != rec["checksum_sha256"].lower():
            raise DiagnosticStopError("checksum_mismatch", f"on-disk digest mismatch vs coverage.json for {oid}")
        pre_digests.append((zip_path, zip_sha))
        pre_digests.append((chk_path, chk_sha))

        parsed_bars, _meta = parse_kline_zip_bytes(
            zip_bytes,
            checksum_text=chk_bytes.decode("utf-8"),
            expected_zip_filename=obj["zip_filename"],
            expected_csv_filename=obj["csv_filename"],
            expected_symbol=obj["symbol"],
            expected_utc_dates=obj["expected_utc_dates"],
        )
        all_bars.extend(parsed_bars)

    analysis = analyze_bars(all_bars, protocol=manifest["protocol"])

    # Post-read integrity check: verify inputs did not mutate during analysis
    for path, expected_sha in pre_digests:
        if _sha256_file(path).lower() != expected_sha.lower():
            raise DiagnosticStopError("checksum_mismatch", f"input mutated during analysis: {path}")
    if _sha256_file(manifest_path).lower() != args.manifest_sha256.lower():
        raise DiagnosticStopError("source_manifest_mismatch", "manifest mutated during analysis")

    results_dir.mkdir(parents=True, exist_ok=False)

    ledger_path = results_dir / "ledger.jsonl"
    with ledger_path.open("w", encoding="utf-8") as fh:
        for cand_name in manifest["protocol"]["candidates"]:
            cand = analysis["candidates"][cand_name]
            ev_by_key = {
                (e["symbol"], e["available_at_ms"]): e for e in cand["event_records"]
            }
            for pt in cand["decision_points"]:
                row = dict(pt)
                key = (pt["symbol"], pt["available_at_ms"])
                if key in ev_by_key:
                    ev = ev_by_key[key]
                    row["control_keys"] = ev["control_keys"]
                    row["control_count"] = ev["control_count"]
                    row["control_mean_bps"] = ev["control_mean_bps"]
                    row["d_bps"] = ev["d_bps"]
                    row["match_status"] = ev["match_status"]
                fh.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")

    summary_payload = {
        "generated_at_utc": _utc_now(),
        "manifest_sha256": args.manifest_sha256.lower(),
        "authority": manifest["authority"],
        "protocol": analysis["protocol"],
        "governance": analysis["governance"],
        "excluded_outside_study_range_bar_counts": analysis["excluded_outside_study_range_bar_counts"],
        "candidates": {
            cand_name: analysis["candidates"][cand_name]["summary"]
            for cand_name in manifest["protocol"]["candidates"]
        },
    }
    _write_json_strict(results_dir / "summary.json", summary_payload)
    (results_dir / "EXECUTION_FINISHED").write_text(
        f"EXECUTION_FINISHED_UTC={_utc_now()}\nNOTE=execution_completed_pending_independent_audit_not_complete\n",
        encoding="utf-8",
    )
    print(f"ANALYZE_FINISHED RESULTS_DIR={results_dir}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage 1.3 fixed-universe mean-return diagnostic CLI (prepare / fetch / analyze)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser("prepare", help="Offline source_manifest.json preparation")
    p_prep.add_argument("--repo-root", required=True)
    p_prep.add_argument("--run-root", required=True)
    p_prep.add_argument("--output", required=True)
    p_prep.add_argument("--design-sha256", required=True)
    p_prep.add_argument("--plan-sha256", required=True)

    p_fetch = sub.add_parser("fetch", help="Bounded public read-only archive fetch and coverage check")
    p_fetch.add_argument("--manifest", required=True)
    p_fetch.add_argument("--manifest-sha256", required=True)

    p_ana = sub.add_parser("analyze", help="Strictly offline re-verification and diagnostic analysis")
    p_ana.add_argument("--manifest", required=True)
    p_ana.add_argument("--manifest-sha256", required=True)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    http_transport: Callable[[str, float], Any] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            return _cmd_prepare(args)
        if args.command == "fetch":
            return _cmd_fetch(args, http_transport=http_transport, sleep_fn=sleep_fn)
        if args.command == "analyze":
            return _cmd_analyze(args)
        raise DiagnosticStopError("source_manifest_mismatch", f"unknown command: {args.command}")
    except DiagnosticStopError as exc:
        print(f"STOP={exc.stop_code} ({exc.detail})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
