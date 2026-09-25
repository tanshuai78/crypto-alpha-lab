"""One-shot collector for Stage 1.6F-W2 minimal historical evidence expansion.

Invariants: INV-W2E01, INV-W2E04, INV-W2E05, INV-W2E06, INV-W2E08, INV-W2E09, INV-W2E11, INV-W2E12, INV-W2E13.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable

from configs.base import (
    EXCHANGE_TIMEOUT_MS,
    EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT,
    EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES,
    EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES,
    EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES,
    EXTERNAL_SIGNAL_STAGE1_6F_W2_MIN_FREE_BYTES,
    EXTERNAL_SIGNAL_STAGE1_6F_W2_REQUEST_INTERVAL_SECONDS,
)
from src.research.external_signal_shadow.stage1_6f_w2_evidence_source import (
    W2_13_FALSE_FLAGS,
    W2_SCHEMA_VERSION,
    compute_w2_metric_coverages,
    derive_w2_authority_inputs,
    derive_w2_request_set,
    load_verified_w2_evidence,
    validate_w2_network_authorization,
    validate_w2_zip_and_csv,
)

FROZEN_CANONICAL_002_MANIFEST_SHA = "b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67"


class W2CollectionError(RuntimeError):
    """Raised when W2 collection fails safety, space, authorization, or transport invariants."""


class DirectProxyHandler(urllib.request.ProxyHandler):
    """Direct proxy handler enforcing no proxies."""

    def __init__(self) -> None:
        urllib.request.ProxyHandler.__init__(self, {})

    def default_open(self, req: Any) -> None:
        return None


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """HTTP redirect handler that unconditionally refuses redirects."""

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


def build_public_archive_opener() -> urllib.request.OpenerDirector:
    """Build isolated stdlib opener with empty proxy and no-redirect handlers."""
    return urllib.request.build_opener(
        DirectProxyHandler(),
        NoRedirectHandler(),
    )


def open_public_archive_get(url: str) -> Any:
    """Execute exactly one authorized HTTPS GET attempt against public archive."""
    opener = build_public_archive_opener()
    request = urllib.request.Request(
        url,
        headers={"User-Agent": EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT},
        method="GET",
    )
    return opener.open(request, timeout=EXCHANGE_TIMEOUT_MS / 1000.0)


def _write_all(fd: int, data: bytes | memoryview) -> None:
    view = memoryview(data)
    total_written = 0
    total_len = len(view)
    while total_written < total_len:
        written = os.write(fd, view[total_written:])
        if written <= 0:
            raise W2CollectionError(f"STOP=w2_write_failed:zero_bytes_written:{total_written}/{total_len}")
        total_written += written


def _atomic_write_file(target_file: Path, data_bytes: bytes) -> None:
    part_file = target_file.parent / f"{target_file.name}.part"
    if part_file.exists():
        part_file.unlink()
    fd = os.open(str(part_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        _write_all(fd, data_bytes)
        os.fsync(fd)
    finally:
        os.close(fd)
    part_file.rename(target_file)
    dir_fd = os.open(str(target_file.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _atomic_stream_copy(src_file: Path, target_file: Path, max_bytes: int) -> None:
    part_file = target_file.parent / f"{target_file.name}.part"
    if part_file.exists():
        part_file.unlink()
    fd = os.open(str(part_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    total_bytes = 0
    try:
        with open(src_file, "rb") as sf:
            while True:
                remaining = max_bytes - total_bytes
                to_read = min(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES, remaining)
                if to_read <= 0:
                    probe = sf.read(1)
                    if probe:
                        raise W2CollectionError(f"STOP=w2_copy_bytes_exceeded_cap:{src_file}")
                    break
                chunk = sf.read(to_read)
                if not chunk:
                    break
                _write_all(fd, chunk)
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise W2CollectionError(f"STOP=w2_copy_bytes_exceeded_cap:{src_file}")
        os.fsync(fd)
    finally:
        os.close(fd)
    part_file.rename(target_file)
    dir_fd = os.open(str(target_file.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def execute_w2_collection_run(
    *,
    project_root: Path,
    c_completed_root: Path,
    b_source_export: Path,
    canonical_002_root: Path,
    coverage_matrix: Path,
    output_root: Path,
    run_id: str,
    approved_design_path: Path,
    approved_design_sha: str,
    approved_plan_path: Path,
    approved_plan_sha: str,
    network_authorization_path: Path,
    network_authorization_sha: str,
    transport: Callable[[str], Any] | None = None,
) -> dict[str, object]:
    """Execute one front-end W2 candidate collection run; caller supplies transport double or production GET."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id):
        raise W2CollectionError(f"STOP=w2_run_id_invalid:{run_id}")

    # 1. Pre-collection Authority and Request Set derivation
    authority = derive_w2_authority_inputs(
        project_root=project_root,
        c_completed_root=c_completed_root,
        b_source_export=b_source_export,
        canonical_002_root=canonical_002_root,
        coverage_matrix=coverage_matrix,
        approved_design_path=approved_design_path,
        approved_design_sha=approved_design_sha,
        approved_plan_path=approved_plan_path,
        approved_plan_sha=approved_plan_sha,
        network_authorization_path=network_authorization_path,
        network_authorization_sha=network_authorization_sha,
    )
    request_set = derive_w2_request_set(authority)

    validate_w2_network_authorization(
        authorization_path=network_authorization_path,
        authorization_sha256=network_authorization_sha,
        design_path=approved_design_path,
        design_sha256=approved_design_sha,
        plan_path=approved_plan_path,
        plan_sha256=approved_plan_sha,
        run_id=run_id,
        request_set=request_set,
    )

    # 2. Check disk free space guard
    check_dir = output_root if output_root.exists() else output_root.parent
    check_dir.mkdir(parents=True, exist_ok=True)
    statv = os.statvfs(str(check_dir))
    free_bytes = statv.f_bavail * statv.f_frsize
    if free_bytes < EXTERNAL_SIGNAL_STAGE1_6F_W2_MIN_FREE_BYTES:
        raise W2CollectionError(
            f"STOP=w2_insufficient_disk_space:{free_bytes}<{EXTERNAL_SIGNAL_STAGE1_6F_W2_MIN_FREE_BYTES}"
        )

    # 3. Create canonical candidate root exclusively
    candidate_root = output_root / run_id
    if candidate_root.exists():
        raise W2CollectionError(f"STOP=w2_candidate_root_already_exists:{candidate_root}")
    zips_dir = candidate_root / "zips"
    csvs_dir = candidate_root / "csvs"
    zips_dir.mkdir(parents=True, exist_ok=False)
    csvs_dir.mkdir(parents=True, exist_ok=False)

    # 4. Copy 9 canonical 002 objects
    c_002_manifest_file = canonical_002_root / "candidate_manifest.json"
    c_002_manifest_bytes_before = c_002_manifest_file.read_bytes()
    c_002_sha_before = hashlib.sha256(c_002_manifest_bytes_before).hexdigest()
    if c_002_sha_before != FROZEN_CANONICAL_002_MANIFEST_SHA:
        raise W2CollectionError(
            f"STOP=w2_002_manifest_tampered:{c_002_sha_before}!={FROZEN_CANONICAL_002_MANIFEST_SHA}"
        )

    verified_002_objs = {
        obj["physical_source_object_id"]: obj
        for obj in authority.verified_002.manifest["physical_source_objects"]
    }

    physical_records_map: dict[str, dict[str, Any]] = {}
    loaded_csv_rows: dict[str, list[dict[str, Any]]] = {}

    for phys in request_set.physical_records:
        pid = phys["physical_source_object_id"]
        if pid in request_set.reuse_ids:
            old_obj = verified_002_objs[pid]
            src_zip = authority.verified_002.completed_root / old_obj["zip_relative_path"]
            src_csv = authority.verified_002.completed_root / old_obj["csv_relative_path"]
            dst_zip = candidate_root / old_obj["zip_relative_path"]
            dst_csv = candidate_root / old_obj["csv_relative_path"]

            _atomic_stream_copy(src_zip, dst_zip, EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES)
            _atomic_stream_copy(src_csv, dst_csv, EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES)

            obj = dict(old_obj)
            obj["acquisition_method"] = "copied_verified_002"
            obj["source_manifest_sha256"] = FROZEN_CANONICAL_002_MANIFEST_SHA
            obj["source_physical_source_object_id"] = pid
            obj["network_attempt_count"] = 0
            obj["http_status_or_transport_error"] = None
            obj["request_started_at_ms"] = None
            obj["response_observed_at_ms"] = None
            obj["reason"] = "canonical_002_reused"
            physical_records_map[pid] = obj

            val_result = validate_w2_zip_and_csv(
                zip_path=dst_zip,
                csv_path=dst_csv,
                expected_url=obj["exact_source_url"],
            )
            loaded_csv_rows[pid] = val_result["parsed_rows"]

    # Verify 002 manifest was untouched
    c_002_sha_after = hashlib.sha256(c_002_manifest_file.read_bytes()).hexdigest()
    if c_002_sha_after != c_002_sha_before:
        raise W2CollectionError("STOP=w2_002_manifest_modified_during_copy")

    # 5. Execute 171 FETCH requests
    fetch_physical = [
        p for p in request_set.physical_records if p["acquisition_method"] == "network_get"
    ]
    fetch_physical.sort(key=lambda x: str(x["exact_source_url"]))

    last_request_time = 0.0

    for phys in fetch_physical:
        pid = phys["physical_source_object_id"]
        url = phys["exact_source_url"]

        if transport is None and last_request_time > 0.0:
            elapsed = time.time() - last_request_time
            if elapsed < EXTERNAL_SIGNAL_STAGE1_6F_W2_REQUEST_INTERVAL_SECONDS:
                time.sleep(EXTERNAL_SIGNAL_STAGE1_6F_W2_REQUEST_INTERVAL_SECONDS - elapsed)

        req_start_ms = int(time.time() * 1000)
        last_request_time = time.time()
        resp_obj: Any = None
        transport_err: str | int | None = None

        try:
            if transport is not None:
                resp_obj = transport(url)
            else:
                resp_obj = open_public_archive_get(url)
        except urllib.error.HTTPError as he:
            transport_err = he.code
        except Exception as ex:
            transport_err = str(ex)

        if transport_err is not None and not isinstance(transport_err, int):
            resp_obs_ms = None
        else:
            resp_obs_ms = int(time.time() * 1000)

        record_entry: dict[str, Any] = {
            "physical_source_object_id": pid,
            "exact_source_url": url,
            "acquisition_method": "network_get",
            "source_manifest_sha256": None,
            "source_physical_source_object_id": None,
            "network_attempt_count": 1,
            "http_status_or_transport_error": transport_err,
            "zip_relative_path": None,
            "zip_byte_length": None,
            "zip_sha256": None,
            "csv_relative_path": None,
            "csv_byte_length": None,
            "csv_sha256": None,
            "zip_member_name": None,
            "csv_header": None,
            "csv_row_count": 0,
            "first_row": None,
            "last_row": None,
            "request_started_at_ms": req_start_ms,
            "response_observed_at_ms": resp_obs_ms,
        }

        if transport_err is not None:
            if transport_err == 404:
                record_entry["fetch_status"] = "archive_not_found_404"
                record_entry["reason"] = "http_status_404"
            elif isinstance(transport_err, int) and 300 <= transport_err < 400:
                record_entry["fetch_status"] = "redirect_refused"
                record_entry["reason"] = f"http_status_{transport_err}"
            else:
                record_entry["fetch_status"] = "transport_inconclusive"
                record_entry["reason"] = f"transport_error:{transport_err}"
            physical_records_map[pid] = record_entry
            continue

        # If we got a response object, stream body up to chunk cap
        status_code = getattr(resp_obj, "status", getattr(resp_obj, "code", 200))
        if status_code != 200:
            if hasattr(resp_obj, "close"):
                try:
                    resp_obj.close()
                except Exception:
                    pass
            record_entry["http_status_or_transport_error"] = status_code
            if status_code == 404:
                record_entry["fetch_status"] = "archive_not_found_404"
                record_entry["reason"] = "http_status_404"
            elif 300 <= status_code < 400:
                record_entry["fetch_status"] = "redirect_refused"
                record_entry["reason"] = f"http_status_{status_code}"
            else:
                record_entry["fetch_status"] = "transport_inconclusive"
                record_entry["reason"] = f"http_status_{status_code}"
            physical_records_map[pid] = record_entry
            continue

        oversize = False
        stream_err: str | None = None
        total_zip_bytes = 0
        zip_hasher = hashlib.sha256()

        target_zip = zips_dir / f"{pid}.zip"
        part_zip = zips_dir / f"{pid}.zip.part"
        if part_zip.exists():
            part_zip.unlink()

        zip_fd = os.open(str(part_zip), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            while True:
                remaining = EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES - total_zip_bytes
                to_read = min(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES, remaining)
                if to_read <= 0:
                    probe = resp_obj.read(1)
                    if probe:
                        oversize = True
                    break
                chunk = resp_obj.read(to_read)
                if not chunk:
                    break
                _write_all(zip_fd, chunk)
                zip_hasher.update(chunk)
                total_zip_bytes += len(chunk)
                if total_zip_bytes > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES:
                    oversize = True
                    break
            os.fsync(zip_fd)
        except Exception as stream_ex:
            stream_err = str(stream_ex)
        finally:
            os.close(zip_fd)
            if hasattr(resp_obj, "close"):
                try:
                    resp_obj.close()
                except Exception:
                    pass

        if stream_err is not None:
            if part_zip.exists():
                part_zip.unlink()
            record_entry["fetch_status"] = "transport_inconclusive"
            record_entry["http_status_or_transport_error"] = stream_err
            record_entry["reason"] = f"stream_error:{stream_err}"
            physical_records_map[pid] = record_entry
            continue

        if oversize:
            if part_zip.exists():
                part_zip.unlink()
            raise W2CollectionError("STOP=w2_resource_budget_exceeded:zip_bytes_exceeded_cap")

        part_zip.rename(target_zip)
        dir_fd = os.open(str(target_zip.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

        zip_sha = zip_hasher.hexdigest()
        zip_len = total_zip_bytes

        # Try to validate and unpack zip
        target_csv = csvs_dir / f"{pid}.csv"
        part_csv = csvs_dir / f"{pid}.csv.part"
        if part_csv.exists():
            part_csv.unlink()

        expected_zip_basename = url.split("/")[-1]
        expected_csv_member = expected_zip_basename[:-4] + ".csv" if expected_zip_basename.endswith(".zip") else expected_zip_basename

        member_name: str | None = None
        try:
            with zipfile.ZipFile(target_zip, "r") as zf:
                infolist = zf.infolist()
                if len(infolist) != 1:
                    raise W2CollectionError("zip_multiple_members")
                info = infolist[0]
                if info.is_dir() or (info.external_attr >> 16 & 0o120000 == 0o120000):
                    raise W2CollectionError("zip_member_not_regular")
                if info.filename != expected_csv_member:
                    raise W2CollectionError(f"zip_member_name_mismatch:{info.filename}!={expected_csv_member}")
                if info.file_size > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES:
                    raise W2CollectionError("STOP=w2_resource_budget_exceeded:csv_bytes_exceeded_cap")
                member_name = info.filename

                csv_fd = os.open(str(part_csv), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                total_csv_bytes = 0
                csv_oversize = False
                try:
                    with zf.open(info, "r") as mf:
                        while True:
                            remaining_csv = EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES - total_csv_bytes
                            to_read_csv = min(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES, remaining_csv)
                            if to_read_csv <= 0:
                                probe_csv = mf.read(1)
                                if probe_csv:
                                    csv_oversize = True
                                break
                            c = mf.read(to_read_csv)
                            if not c:
                                break
                            _write_all(csv_fd, c)
                            total_csv_bytes += len(c)
                            if total_csv_bytes > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES:
                                csv_oversize = True
                                break
                    os.fsync(csv_fd)
                finally:
                    os.close(csv_fd)

                if csv_oversize:
                    if part_csv.exists():
                        part_csv.unlink()
                    raise W2CollectionError("STOP=w2_resource_budget_exceeded:csv_bytes_exceeded_cap")

                part_csv.rename(target_csv)
                dir_fd = os.open(str(target_csv.parent), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
        except Exception as zip_ex:
            if isinstance(zip_ex, W2CollectionError) and "STOP=w2_resource_budget_exceeded" in str(zip_ex):
                raise
            if part_csv.exists():
                part_csv.unlink()
            if target_csv.exists():
                target_csv.unlink()
            record_entry["fetch_status"] = "archive_invalid"
            record_entry["http_status_or_transport_error"] = 200
            record_entry["reason"] = f"archive_invalid:{zip_ex}"
            record_entry["zip_relative_path"] = f"zips/{target_zip.name}"
            record_entry["zip_byte_length"] = zip_len
            record_entry["zip_sha256"] = zip_sha
            physical_records_map[pid] = record_entry
            continue

        try:
            val_result = validate_w2_zip_and_csv(
                zip_path=target_zip,
                csv_path=target_csv,
                expected_url=url,
            )
            loaded_csv_rows[pid] = val_result["parsed_rows"]
            record_entry["fetch_status"] = "fetched_verified"
            record_entry["http_status_or_transport_error"] = 200
            record_entry["reason"] = "public_archive_download_success"
            record_entry["zip_relative_path"] = f"zips/{target_zip.name}"
            record_entry["zip_byte_length"] = val_result["zip_byte_length"]
            record_entry["zip_sha256"] = val_result["zip_sha256"]
            record_entry["csv_relative_path"] = f"csvs/{target_csv.name}"
            record_entry["csv_byte_length"] = val_result["csv_byte_length"]
            record_entry["csv_sha256"] = val_result["csv_sha256"]
            record_entry["zip_member_name"] = val_result["zip_member_name"]
            record_entry["csv_header"] = val_result["csv_header"]
            record_entry["csv_row_count"] = val_result["csv_row_count"]
            record_entry["first_row"] = val_result["first_row"]
            record_entry["last_row"] = val_result["last_row"]
        except Exception as csv_val_ex:
            csv_len = target_csv.stat().st_size
            csv_sha = hashlib.sha256()
            with open(target_csv, "rb") as cf:
                while True:
                    ch = cf.read(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES)
                    if not ch:
                        break
                    csv_sha.update(ch)

            record_entry["fetch_status"] = "csv_invalid"
            record_entry["http_status_or_transport_error"] = 200
            record_entry["reason"] = f"csv_invalid:{csv_val_ex}"
            record_entry["zip_relative_path"] = f"zips/{target_zip.name}"
            record_entry["zip_byte_length"] = zip_len
            record_entry["zip_sha256"] = zip_sha
            record_entry["csv_relative_path"] = f"csvs/{target_csv.name}"
            record_entry["csv_byte_length"] = csv_len
            record_entry["csv_sha256"] = csv_sha.hexdigest()
            record_entry["zip_member_name"] = member_name
            raw_hdr: str | None = None
            try:
                with open(target_csv, "r", encoding="utf-8") as cf:
                    first_line = cf.readline()
                    if first_line:
                        raw_hdr = first_line.rstrip("\r\n")
            except Exception:
                raw_hdr = None
            record_entry["csv_header"] = raw_hdr
            record_entry["csv_row_count"] = 0
            record_entry["first_row"] = None
            record_entry["last_row"] = None

        physical_records_map[pid] = record_entry

    # 6. Aggregate Coverages
    logical_records = []
    for log_rec in request_set.logical_records:
        rec = dict(log_rec)
        pid = rec["physical_source_object_id"]
        rec["record_state"] = physical_records_map[pid]["fetch_status"]
        logical_records.append(rec)

    physical_records = [
        physical_records_map[p["physical_source_object_id"]]
        for p in request_set.physical_records
    ]

    metric_coverages = compute_w2_metric_coverages(
        authority.denominator_records,
        logical_records,
        physical_records_map,
        loaded_csv_rows,
    )

    all_complete = (
        len(metric_coverages) == 123
        and all(c["complete_bar_status"] == "observed" for c in metric_coverages)
    )
    root_state = (
        "collection_terminal_all_complete_bars"
        if all_complete
        else "collection_terminal_with_evidence_gaps"
    )

    # 7. Build Manifest Data
    frozen_inputs = [
        {"path": k, "sha256": v}
        for k, v in sorted({
            approved_design_path.name: approved_design_sha,
            approved_plan_path.name: approved_plan_sha,
        }.items())
    ]
    # Use workspace relative path for network authorization
    try:
        rel_auth_p = str(network_authorization_path.relative_to(project_root))
    except ValueError:
        rel_auth_p = str(network_authorization_path)

    manifest_data = {
        "schema_version": W2_SCHEMA_VERSION,
        "run_id": run_id,
        "authority_packet": {
            "frozen_inputs": frozen_inputs,
            "approved_design": {
                "path": str(approved_design_path),
                "sha256": approved_design_sha,
            },
            "approved_plan": {
                "path": str(approved_plan_path),
                "sha256": approved_plan_sha,
            },
            "network_authorization": {
                "path": rel_auth_p,
                "sha256": network_authorization_sha,
                "run_id": run_id,
            },
        },
        "denominator_records": list(authority.denominator_records),
        "logical_archive_records": logical_records,
        "physical_source_objects": physical_records,
        "metric_window_coverages": list(metric_coverages),
        "request_set": {
            "all_urls_sha256": request_set.all_urls_sha256,
            "reuse_urls_sha256": request_set.reuse_urls_sha256,
            "fetch_urls_sha256": request_set.fetch_urls_sha256,
            "n_logical": len(request_set.logical_records),
            "n_physical": len(request_set.physical_records),
            "n_reused": len(request_set.reuse_ids),
            "n_network_attempts": len(request_set.fetch_ids),
        },
        "candidate_root_state": root_state,
        "capture_mode": "historical_ex_post_candidate",
        "point_in_time_source_validated": False,
        "authority_flags": dict(W2_13_FALSE_FLAGS),
    }

    manifest_path = candidate_root / "candidate_manifest.json"
    manifest_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")
    _atomic_write_file(manifest_path, manifest_bytes)

    # 8. Reopen through independent Class A validator
    load_verified_w2_evidence(
        project_root=project_root,
        candidate_root=candidate_root,
        approved_design_path=approved_design_path,
        approved_design_sha=approved_design_sha,
        approved_plan_path=approved_plan_path,
        approved_plan_sha=approved_plan_sha,
        network_authorization_path=network_authorization_path,
        network_authorization_sha=network_authorization_sha,
    )

    return {
        "candidate_root": candidate_root,
        "candidate_manifest_path": manifest_path,
        "candidate_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "candidate_root_state": root_state,
        "n_physical_objects": len(physical_records),
        "n_metric_coverages": len(metric_coverages),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Stage 1.6F-W2 historical evidence candidate expansion collection."
    )
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--c-completed-root", type=Path, required=True)
    parser.add_argument("--b-source-export", type=Path, required=True)
    parser.add_argument("--canonical-002-root", type=Path, required=True)
    parser.add_argument("--coverage-matrix", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--approved-design-path", type=Path, required=True)
    parser.add_argument("--approved-design-sha", type=str, required=True)
    parser.add_argument("--approved-plan-path", type=Path, required=True)
    parser.add_argument("--approved-plan-sha", type=str, required=True)
    parser.add_argument("--network-authorization-path", type=Path, required=True)
    parser.add_argument("--network-authorization-sha", type=str, required=True)
    parser.add_argument(
        "--live-public-readonly",
        action="store_true",
        default=False,
        help="Explicitly permit readonly public archive requests under approved network authorization.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
    except SystemExit as se:
        return int(se.code) if isinstance(se.code, int) else 2

    if not args.live_public_readonly:
        sys.stderr.write(
            "STOP=w2_cli_flag_missing: --live-public-readonly is required to initiate W2 public archive collection.\n"
        )
        return 1

    try:
        result = execute_w2_collection_run(
            project_root=args.project_root,
            c_completed_root=args.c_completed_root,
            b_source_export=args.b_source_export,
            canonical_002_root=args.canonical_002_root,
            coverage_matrix=args.coverage_matrix,
            output_root=args.output_root,
            run_id=args.run_id,
            approved_design_path=args.approved_design_path,
            approved_design_sha=args.approved_design_sha,
            approved_plan_path=args.approved_plan_path,
            approved_plan_sha=args.approved_plan_sha,
            network_authorization_path=args.network_authorization_path,
            network_authorization_sha=args.network_authorization_sha,
            transport=None,
        )
        sys.stdout.write(
            f"W2_COLLECTION_COMPLETE: run_id={args.run_id} "
            f"candidate_root_state={result['candidate_root_state']} "
            f"candidate_manifest_sha256={result['candidate_manifest_sha256']}\n"
        )
        return 0
    except Exception as e:
        sys.stderr.write(f"W2_COLLECTION_FAILED: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
