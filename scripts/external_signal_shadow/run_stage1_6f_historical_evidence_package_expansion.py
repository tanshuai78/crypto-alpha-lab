"""Historical evidence package expansion collector and validator.

Stage 1.6F historical archive candidate collector.
Zero-permission boundary: RISK_LIVE_TRADING_ENABLED = False.
Strictly offline / double test capability.
"""

import argparse
import csv
import datetime
import hashlib
import io
import json
import math
import os
import socket
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
import zlib
from datetime import timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from configs.base import EXCHANGE_TIMEOUT_MS, EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    ALL_PERMISSION_FLAGS_FALSE,
    reconstruct_denominator,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    VerifiedCInput,
    verify_c_input,
)


class CandidateCollectorError(Exception):
    """Base error for candidate collection and validation."""
    pass


class AuthorityMismatchError(CandidateCollectorError):
    """Raised when an approved authority hash or authorization input mismatches."""
    pass


SCHEMA_VERSION = "stage1_6f_historical_evidence_expansion_candidate_manifest_v1"

EXPECTED_11_MANIFEST_KEYS: Set[str] = {
    "schema_version",
    "run_id",
    "authority_packet",
    "cohort",
    "physical_source_objects",
    "logical_archive_records",
    "metric_window_coverages",
    "candidate_root_state",
    "capture_mode",
    "point_in_time_source_validated",
    "authority_flags",
}

EXPECTED_13_AUTHORITY_PACKET_KEYS: Set[str] = {
    "parent_f_design",
    "f_evidence_to_schema_delta",
    "approved_f_implementation_plan",
    "existing_reef_evidence_manifest",
    "archive_coverage_matrix",
    "c_completion_manifest",
    "c_source_export_receipt",
    "b_sealed_export_manifest",
    "f_denominator_module",
    "f_source_module",
    "approved_historical_evidence_expansion_design",
    "approved_expansion_implementation_plan",
    "network_collection_authorization",
}

ZIP_EXTRACT_CHUNK_SIZE: int = 64 * 1024

EXPECTED_PHYSICAL_OBJECT_KEYS: Set[str] = {
    "physical_source_object_id",
    "exact_source_url",
    "fetch_status",
    "http_status_or_transport_error",
    "zip_relative_path",
    "zip_byte_length",
    "zip_sha256",
    "csv_relative_path",
    "csv_byte_length",
    "csv_sha256",
    "zip_member_name",
    "csv_header",
    "csv_row_count",
    "first_row",
    "last_row",
    "request_started_at_ms",
    "response_observed_at_ms",
    "reason",
}

EXPECTED_LOGICAL_RECORD_KEYS: Set[str] = {
    "logical_archive_record_id",
    "parent_article_id",
    "contract_id",
    "canonical_symbol",
    "window",
    "nominal_window_start_utc",
    "window_start_utc",
    "window_end_utc",
    "metric",
    "archive_date_or_month",
    "exact_source_url",
    "coverage_matrix_sha256",
    "matrix_record_sha256",
    "physical_source_object_id",
    "matrix_record_projection_v1",
    "record_state",
    "reason",
    "parsed_window_row_count",
    "observed_first_timestamp_ms",
    "observed_last_timestamp_ms",
    "duplicate_count",
    "conflict_count",
    "gap_count",
}

EXPECTED_METRIC_WINDOW_COVERAGE_KEYS: Set[str] = {
    "parent_article_id",
    "contract_id",
    "canonical_symbol",
    "window",
    "metric",
    "timestamp_key",
    "requested_interval_start_ms",
    "requested_interval_end_ms",
    "expected_grid_step_ms",
    "parsed_window_row_count",
    "observed_first_timestamp_ms",
    "observed_last_timestamp_ms",
    "duplicate_count",
    "conflict_count",
    "gap_count",
    "coverage_status",
    "reason",
}

EXACT_EXPECTED_13_FALSE_MAPPING: Dict[str, bool] = {
    "RISK_LIVE_TRADING_ENABLED": False,
    "trade_signal_allowed": False,
    "paper_trading_allowed": False,
    "live_trading_allowed": False,
    "execution_engine_allowed": False,
    "private_api_allowed": False,
    "authenticated_api_allowed": False,
    "order_api_allowed": False,
    "alpha_interpretation_allowed": False,
    "execution_feasibility_claim_allowed": False,
    "net_cost_or_profit_claim_allowed": False,
    "replay_allowed": False,
    "point_in_time_directional_replay_allowed": False,
}

PERMITTED_WINDOWS_METRICS: Dict[str, Set[str]] = {
    "baseline_168h": {"klines_1h"},
    "w1_shock_12h": {
        "klines_1h",
        "index_price_1h",
        "mark_price_1h",
        "premium_index_1h",
        "funding_rate",
        "metrics_5m",
        "book_depth",
        "agg_trades",
    },
}

EXACT_AUTHORITY_FILES: Dict[str, str] = {
    "parent_f_design": "87c270bd52e7547eba547d5abcd8ee10287f53183e5389446697831213832d1c",
    "f_evidence_to_schema_delta": "8ddc7ae9927854dd2b4279d6df4d192e0eac09a3ee7163a0a546bb7e815e8628",
    "approved_f_implementation_plan": "6ed3865ce026a2392c5ecd80f2a78bbb6ef36054bdc79eda28aeea68ba342e2f",
    "existing_reef_evidence_manifest": "9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f",
    "archive_coverage_matrix": "b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8",
    "c_completion_manifest": "226b41ca415520fbe1510cad53e34b6f48586ff159b525cf09becb3fe71d3fb0",
    "c_source_export_receipt": "07578a02f4e76cd8f041fb4fea4e0fc100213ee1f98b85bbf2f702ad5540d30e",
    "b_sealed_export_manifest": "1d6804f0e02e0eb0f6db807de5c63a63d0e9cdc8f950c897dcb25820d13db0be",
    "f_denominator_module": "84fa59fc0a6f1392688558affa2567ae79be53d6bcbff82e8f3c30e4081ad2d3",
    "f_source_module": "00183d35684d5ee340f8e7424b9f1ac4a1ed7faee1c0f14b5cb0c7f02007da4f",
}

FIXED_AUTHORITY_KEY_MAP: Dict[str, str] = {
    "docs/designs/2026-09-12-external-signal-shadow-lab-stage1-6f-historical-matched-control-mechanism-diagnostic-design_CN.md": "parent_f_design",
    "docs/designs/2026-09-14-external-signal-shadow-lab-stage1-6f-evidence-to-schema-delta-design_CN.md": "f_evidence_to_schema_delta",
    "docs/plans/2026-09-14-external-signal-shadow-lab-stage1-6f-historical-mechanism-diagnostic-implementation-plan_CN.md": "approved_f_implementation_plan",
    "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/gap02_evidence_manifest.json": "existing_reef_evidence_manifest",
    "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json": "archive_coverage_matrix",
    "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json": "c_completion_manifest",
    "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/source_export_receipt.json": "c_source_export_receipt",
    "data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090/sealed_export_manifest.json": "b_sealed_export_manifest",
    "src/research/external_signal_shadow/stage1_6f_historical_diagnostic.py": "f_denominator_module",
    "src/research/external_signal_shadow/stage1_6f_historical_diagnostic_source.py": "f_source_module",
}

EXACT_CSV_HEADERS: Dict[str, str] = {
    "klines_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "mark_price_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "index_price_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "premium_index_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "metrics_5m": "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio",
    "funding_rate": "calc_time,funding_interval_hours,last_funding_rate",
    "book_depth": "timestamp,percentage,depth,notional",
    "agg_trades": "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
}

GRID_STEP_MS: Dict[str, Optional[int]] = {
    "klines_1h": 3_600_000,
    "mark_price_1h": 3_600_000,
    "index_price_1h": 3_600_000,
    "premium_index_1h": 3_600_000,
    "metrics_5m": 300_000,
    "funding_rate": None,
    "book_depth": None,
    "agg_trades": None,
}

TIMESTAMP_KEYS: Dict[str, str] = {
    "klines_1h": "open_time",
    "mark_price_1h": "open_time",
    "index_price_1h": "open_time",
    "premium_index_1h": "open_time",
    "metrics_5m": "create_time",
    "funding_rate": "calc_time",
    "book_depth": "timestamp",
    "agg_trades": "transact_time",
}

BOOK_DEPTH_REQUIRED_PERCENTAGES: Set[int] = {-5, -4, -3, -2, -1, 1, 2, 3, 4, 5}


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler that refuses redirects per INV-EP03."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_canonical_opener() -> urllib.request.OpenerDirector:
    """Build standard-library opener refusing redirects and using direct proxy."""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirectHandler())


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of file bytes using chunked streaming."""
    if not path.is_file():
        raise AuthorityMismatchError(f"STOP=approved_authority_mismatch:file_not_found:{path}")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def compute_logical_archive_record_id(record_list: List[Any]) -> str:
    """Canonical JSON SHA-256 for logical archive record tuple."""
    serialized = json.dumps(record_list, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_physical_source_object_id(exact_source_url: str) -> str:
    """Canonical JSON SHA-256 for physical source object URL string."""
    serialized = json.dumps(exact_source_url, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_authority_flags() -> Dict[str, bool]:
    """Return the exact 13 authority flags, all boolean False."""
    return dict(ALL_PERMISSION_FLAGS_FALSE)


def derive_candidate_cohort(
    verified_c: VerifiedCInput,
    coverage_matrix_path: Path,
) -> List[str]:
    """Derive exact 41-symbol candidate cohort from verified C and frozen coverage matrix."""
    denominator_rows = reconstruct_denominator(verified_c)
    eligible_symbols = {r.symbol for r in denominator_rows if r.eligibility_passed}

    matrix_bytes = coverage_matrix_path.read_bytes()
    matrix_data = json.loads(matrix_bytes.decode("utf-8"))
    in_range_records = matrix_data.get("in_range_archive_records", [])
    in_range_symbols = {r["symbol"] for r in in_range_records if "symbol" in r}

    cohort = sorted((eligible_symbols & in_range_symbols) - {"REEFUSDT"})
    if len(cohort) != 41:
        raise AuthorityMismatchError(
            f"STOP=candidate_cohort_authority_mismatch:expected 41 symbols, got {len(cohort)}"
        )
    return cohort


def enumerate_candidate_requests(
    coverage_matrix_path: Path,
    cohort: List[str],
) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Enumerate the 705 logical records and 664 physical objects for the cohort."""
    matrix_bytes = coverage_matrix_path.read_bytes()
    matrix_sha = hashlib.sha256(matrix_bytes).hexdigest()
    matrix_data = json.loads(matrix_bytes.decode("utf-8"))

    in_range_records = matrix_data.get("in_range_archive_records", [])
    cohort_set = set(cohort)

    selected_records: List[Dict[str, Any]] = []
    for r in in_range_records:
        sym = r.get("symbol")
        if sym in cohort_set:
            win = r.get("window")
            met = r.get("metric")
            if win in PERMITTED_WINDOWS_METRICS and met in PERMITTED_WINDOWS_METRICS[win]:
                selected_records.append(r)

    # Sort selected records deterministically by primary keys
    selected_records.sort(
        key=lambda x: (
            x["parent_article_id"],
            x["contract_id"],
            x["symbol"],
            x["window"],
            x["metric"],
            x["archive_date_or_month"],
        )
    )

    logical_archive_records: List[Dict[str, Any]] = []
    physical_objects_map: Dict[str, Dict[str, Any]] = {}

    for r in selected_records:
        parent_article_id = r["parent_article_id"]
        contract_id = r["contract_id"]
        canonical_symbol = r["symbol"]
        window = r["window"]
        nominal_window_start_utc = r["nominal_window_start_utc"]
        window_start_utc = r["window_start_utc"]
        window_end_utc = r["window_end_utc"]
        metric = r["metric"]
        archive_date_or_month = r["archive_date_or_month"]
        exact_source_url = r["url"]

        record_list = [
            parent_article_id,
            contract_id,
            canonical_symbol,
            window,
            nominal_window_start_utc,
            window_start_utc,
            window_end_utc,
            metric,
            archive_date_or_month,
            exact_source_url,
        ]
        logical_id = compute_logical_archive_record_id(record_list)
        physical_id = compute_physical_source_object_id(exact_source_url)

        full_row_canonical = json.dumps(r, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        matrix_record_sha = hashlib.sha256(full_row_canonical.encode("utf-8")).hexdigest()

        logical_entry = {
            "logical_archive_record_id": logical_id,
            "parent_article_id": parent_article_id,
            "contract_id": contract_id,
            "canonical_symbol": canonical_symbol,
            "window": window,
            "nominal_window_start_utc": nominal_window_start_utc,
            "window_start_utc": window_start_utc,
            "window_end_utc": window_end_utc,
            "metric": metric,
            "archive_date_or_month": archive_date_or_month,
            "exact_source_url": exact_source_url,
            "coverage_matrix_sha256": matrix_sha,
            "matrix_record_sha256": matrix_record_sha,
            "physical_source_object_id": physical_id,
            "matrix_record_projection_v1": {
                "parent_article_id": parent_article_id,
                "contract_id": contract_id,
                "canonical_symbol": canonical_symbol,
                "window": window,
                "nominal_window_start_utc": nominal_window_start_utc,
                "window_start_utc": window_start_utc,
                "window_end_utc": window_end_utc,
                "metric": metric,
                "archive_date_or_month": archive_date_or_month,
                "exact_source_url": exact_source_url,
            },
        }
        logical_archive_records.append(logical_entry)

        if physical_id not in physical_objects_map:
            physical_objects_map[physical_id] = {
                "physical_source_object_id": physical_id,
                "exact_source_url": exact_source_url,
            }

    physical_objects = [physical_objects_map[k] for k in sorted(physical_objects_map.keys())]
    return matrix_sha, logical_archive_records, physical_objects


def validate_prefetch_authority(
    project_root: Path,
    source_export: Path,
    completed_root: Path,
    coverage_matrix: Path,
    approved_design_path: Path,
    approved_design_sha: str,
    approved_plan_path: Path,
    approved_plan_sha: str,
    network_authorization_file: Path,
    network_authorization_sha: str,
    run_id: str,
) -> Dict[str, Any]:
    """Prefetch authority gate. Validates all inputs before opening a connection or root."""
    actual_design_sha = compute_file_sha256(approved_design_path)
    if actual_design_sha != approved_design_sha:
        raise AuthorityMismatchError(
            f"STOP=approved_authority_mismatch:design:{actual_design_sha}!={approved_design_sha}"
        )

    actual_plan_sha = compute_file_sha256(approved_plan_path)
    if actual_plan_sha != approved_plan_sha:
        raise AuthorityMismatchError(
            f"STOP=approved_authority_mismatch:plan:{actual_plan_sha}!={approved_plan_sha}"
        )

    actual_auth_file_sha = compute_file_sha256(network_authorization_file)
    if actual_auth_file_sha != network_authorization_sha:
        raise AuthorityMismatchError(
            f"STOP=approved_authority_mismatch:network_auth_sha:{actual_auth_file_sha}!={network_authorization_sha}"
        )

    auth_raw = network_authorization_file.read_bytes()
    try:
        auth_json = json.loads(auth_raw.decode("utf-8"))
    except Exception as e:
        raise AuthorityMismatchError(f"STOP=approved_authority_mismatch:invalid_auth_json:{e}")

    required_auth_keys = {"run_id", "approved_design_sha256", "approved_plan_sha256"}
    if set(auth_json.keys()) != required_auth_keys:
        raise AuthorityMismatchError(
            f"STOP=approved_authority_mismatch:auth_keys_mismatch:{set(auth_json.keys())}"
        )

    if auth_json["run_id"] != run_id:
        raise AuthorityMismatchError(
            f"STOP=approved_authority_mismatch:run_id_mismatch:{auth_json['run_id']}!={run_id}"
        )
    if auth_json["approved_design_sha256"] != approved_design_sha:
        raise AuthorityMismatchError(
            "STOP=approved_authority_mismatch:auth_design_sha_mismatch"
        )
    if auth_json["approved_plan_sha256"] != approved_plan_sha:
        raise AuthorityMismatchError(
            "STOP=approved_authority_mismatch:auth_plan_sha_mismatch"
        )

    for rel_p, key in FIXED_AUTHORITY_KEY_MAP.items():
        auth_file_path = project_root / rel_p
        if not auth_file_path.is_file():
            raise AuthorityMismatchError(
                f"STOP=approved_authority_mismatch:missing_workspace_authority:{key}:{rel_p}"
            )
        act_sha = compute_file_sha256(auth_file_path)
        exp_sha = EXACT_AUTHORITY_FILES[key]
        if act_sha != exp_sha:
            raise AuthorityMismatchError(
                f"STOP=approved_authority_mismatch:{key}:{act_sha}!={exp_sha}"
            )

    verified_c = verify_c_input(
        project_root=project_root,
        completed_root=completed_root,
        source_export=source_export,
    )

    cohort = derive_candidate_cohort(verified_c, coverage_matrix)
    matrix_sha, logical_records, physical_objects = enumerate_candidate_requests(
        coverage_matrix, cohort
    )

    return {
        "verified_c": verified_c,
        "cohort": cohort,
        "matrix_sha": matrix_sha,
        "logical_records": logical_records,
        "physical_objects": physical_objects,
        "authorization_record_sha256": actual_auth_file_sha,
    }


class StreamedCsvPath(type(Path())):
    """A Path representing an isolated on-disk CSV stream that satisfies len() and equality checks."""

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, (bytes, bytearray)):
            return self.read_bytes() == bytes(other)
        if isinstance(other, str):
            return str(self) == other
        return super().__eq__(other)

    def __len__(self) -> int:
        return self.stat().st_size


def validate_zip_member(
    zip_bytes: bytes,
    target_csv_file: Optional[Path] = None,
) -> Tuple[str, str, Optional[str], Optional[StreamedCsvPath]]:
    """Strictly validates single ZIP member safety per Section 5.3 without whole-file memory buffering."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except Exception as exc:
        return "archive_invalid", f"corrupt_zip:{exc}", None, None

    with zf:
        infolist = zf.infolist()
        if len(infolist) == 0:
            return "archive_invalid", "empty_zip", None, None
        if len(infolist) > 1:
            return "archive_invalid", f"multiple_zip_members:{len(infolist)}", None, None

        member = infolist[0]
        if member.is_dir():
            return "archive_invalid", "directory_zip_member", None, None

        if (member.flag_bits & 0x1) != 0:
            return "archive_invalid", "encrypted_zip_member", None, None

        # Check symlink-like mode: 0o120000
        if ((member.external_attr >> 16) & 0o170000) == 0o120000:
            return "archive_invalid", "symlink_zip_member", None, None

        name = member.filename
        if not name.endswith(".csv"):
            return "archive_invalid", f"non_csv_member_extension:{name}", None, None
        if name.startswith("/") or name.startswith("\\"):
            return "archive_invalid", f"absolute_path_member:{name}", None, None
        if ".." in name or "/" in name or "\\" in name:
            return "archive_invalid", f"path_traversal_member:{name}", None, None
        if not name.replace(".csv", "").strip():
            return "archive_invalid", "empty_csv_basename", None, None

        # Bounded chunk streaming directly to isolated temp file with incremental CRC32 computation
        if target_csv_file is not None:
            temp_path = Path(target_csv_file)
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_f = open(temp_path, "wb")
        else:
            tf = tempfile.NamedTemporaryFile(prefix="stage1_6f_stream_", suffix=".csv", delete=False)
            temp_path = Path(tf.name)
            tmp_f = tf

        total_read = 0
        running_crc = 0
        try:
            with zf.open(member) as stream:
                while True:
                    chunk = stream.read(ZIP_EXTRACT_CHUNK_SIZE)
                    if not chunk:
                        break
                    total_read += len(chunk)
                    if total_read > member.file_size:
                        tmp_f.close()
                        temp_path.unlink(missing_ok=True)
                        return "archive_invalid", f"member_size_exceeded:{total_read}>{member.file_size}", None, None
                    running_crc = zlib.crc32(chunk, running_crc)
                    tmp_f.write(chunk)
            tmp_f.flush()
            tmp_f.close()
        except Exception as exc:
            try:
                tmp_f.close()
            except Exception:
                pass
            temp_path.unlink(missing_ok=True)
            return "archive_invalid", f"zip_member_read_error:{exc}", None, None

        if total_read != member.file_size:
            temp_path.unlink(missing_ok=True)
            return "archive_invalid", f"member_size_mismatch:{total_read}!={member.file_size}", None, None

        actual_crc = running_crc & 0xFFFFFFFF
        if actual_crc != member.CRC:
            temp_path.unlink(missing_ok=True)
            return "archive_invalid", f"zip_crc_mismatch:{actual_crc}!={member.CRC}", None, None

        return "fetched_verified", "ok", name, StreamedCsvPath(temp_path)


def _parse_timestamp_ms(raw_val: str) -> int:
    """Parse integer ms or YYYY-MM-DD HH:MM:SS string to epoch ms."""
    s = raw_val.strip()
    if s.isdigit():
        return int(s)
    if s.startswith("-") and s[1:].isdigit():
        raise ValueError(f"negative_timestamp:{s}")
    dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _parse_nonnegative_int(val: str, field_name: str) -> int:
    """Strictly parse non-negative integer string without coercion."""
    s = val.strip()
    if not s or not s.isdigit():
        raise ValueError(f"invalid_nonnegative_int:{field_name}:{val}")
    return int(s)


def _parse_finite_float(val: str, field_name: str) -> float:
    """Strictly parse finite float string without NaN, Inf, or empty."""
    s = val.strip()
    if not s:
        raise ValueError(f"empty_float:{field_name}")
    f = float(s)
    if not math.isfinite(f):
        raise ValueError(f"non_finite_float:{field_name}:{val}")
    return f


def parse_and_validate_csv(
    family: str,
    csv_source: Union[bytes, Path, str],
    expected_symbol: Optional[str] = None,
) -> Tuple[str, str, Optional[str], int, Optional[str], Optional[str], List[Dict[str, Any]]]:
    """Strictly parses CSV according to Section 5.4 family definitions without whole-file memory buffering."""
    if family not in EXACT_CSV_HEADERS:
        return "csv_invalid", f"unknown_family:{family}", None, 0, None, None, []

    expected_header = EXACT_CSV_HEADERS[family]

    file_handle = None
    try:
        if isinstance(csv_source, (str, Path)) and (isinstance(csv_source, Path) or ("\n" not in csv_source and "\r" not in csv_source)):
            src_path = Path(csv_source)
            if not src_path.is_file():
                return "csv_invalid", f"csv_file_not_found:{src_path}", None, 0, None, None, []
            file_handle = open(src_path, "r", encoding="utf-8", errors="strict")
            line_iter = file_handle
        elif isinstance(csv_source, (bytes, bytearray)):
            try:
                line_iter = io.StringIO(csv_source.decode("utf-8"))
            except Exception as exc:
                return "csv_invalid", f"utf8_decode_error:{exc}", None, 0, None, None, []
        elif isinstance(csv_source, str):
            line_iter = io.StringIO(csv_source)
        else:
            return "csv_invalid", f"unsupported_csv_source_type:{type(csv_source)}", None, 0, None, None, []

        try:
            header_line = line_iter.readline()
        except UnicodeDecodeError as exc:
            return "csv_invalid", f"utf8_decode_error:{exc}", None, 0, None, None, []

        if not header_line:
            return "csv_invalid", "empty_csv", None, 0, None, None, []

        raw_header = header_line.rstrip("\r\n")
        if raw_header != expected_header:
            return "csv_invalid", f"header_mismatch:{raw_header}", raw_header, 0, None, None, []

        parsed_rows: List[Dict[str, Any]] = []
        first_row_str: Optional[str] = None
        last_row_str: Optional[str] = None

        # Track book_depth snapshots
        depth_ladder_by_ts: Dict[int, Set[int]] = {}

        for row_idx, raw_line in enumerate(line_iter, start=1):
            line_clean = raw_line.rstrip("\r\n")
            if not line_clean.strip():
                continue
            if first_row_str is None:
                first_row_str = line_clean
            last_row_str = line_clean

            try:
                parts = next(csv.reader([line_clean]))
            except Exception as exc:
                return "csv_invalid", f"row_parse_error:{row_idx}:{exc}", raw_header, 0, None, None, []

            try:
                if family in {"klines_1h", "mark_price_1h", "index_price_1h", "premium_index_1h"}:
                    if len(parts) != 12:
                        return "csv_invalid", f"invalid_column_count:{len(parts)}", raw_header, 0, None, None, []
                    open_time = _parse_nonnegative_int(parts[0], "open_time")
                    open_p = _parse_finite_float(parts[1], "open")
                    high_p = _parse_finite_float(parts[2], "high")
                    low_p = _parse_finite_float(parts[3], "low")
                    close_p = _parse_finite_float(parts[4], "close")
                    vol = _parse_finite_float(parts[5], "volume")
                    close_time = _parse_nonnegative_int(parts[6], "close_time")
                    quote_vol = _parse_finite_float(parts[7], "quote_volume")
                    count = _parse_nonnegative_int(parts[8], "count")
                    tb_vol = _parse_finite_float(parts[9], "taker_buy_volume")
                    tb_quote_vol = _parse_finite_float(parts[10], "taker_buy_quote_volume")
                    _parse_finite_float(parts[11], "ignore")

                    if family in {"klines_1h", "mark_price_1h", "index_price_1h"}:
                        if open_p < 0 or high_p < 0 or low_p < 0 or close_p < 0:
                            raise ValueError(f"negative_price:{open_p},{high_p},{low_p},{close_p}")
                    if vol < 0 or quote_vol < 0 or count < 0 or tb_vol < 0 or tb_quote_vol < 0:
                        raise ValueError("negative_volume_or_count")
                    if close_time < open_time:
                        raise ValueError(f"close_time_before_open_time:{close_time}<{open_time}")

                    parsed_rows.append({"open_time": open_time})

                elif family == "metrics_5m":
                    if len(parts) != 8:
                        return "csv_invalid", f"invalid_column_count:{len(parts)}", raw_header, 0, None, None, []
                    symbol = parts[1].strip()
                    if not symbol:
                        raise ValueError("empty_symbol")
                    if expected_symbol is not None and symbol != expected_symbol:
                        return "csv_invalid", f"symbol_mismatch:{symbol}!={expected_symbol}", raw_header, 0, None, None, []
                    create_time = _parse_timestamp_ms(parts[0])
                    _parse_finite_float(parts[2], "sum_open_interest")
                    _parse_finite_float(parts[3], "sum_open_interest_value")
                    _parse_finite_float(parts[4], "count_toptrader_long_short_ratio")
                    _parse_finite_float(parts[5], "sum_toptrader_long_short_ratio")
                    _parse_finite_float(parts[6], "count_long_short_ratio")
                    _parse_finite_float(parts[7], "sum_taker_long_short_vol_ratio")
                    parsed_rows.append({"create_time": create_time, "symbol": symbol})

                elif family == "funding_rate":
                    if len(parts) != 3:
                        return "csv_invalid", f"invalid_column_count:{len(parts)}", raw_header, 0, None, None, []
                    calc_time = _parse_nonnegative_int(parts[0], "calc_time")
                    funding_interval = _parse_finite_float(parts[1], "funding_interval_hours")
                    if funding_interval <= 0:
                        raise ValueError(f"invalid_funding_interval:{funding_interval}")
                    funding_rate = _parse_finite_float(parts[2], "last_funding_rate")
                    parsed_rows.append({"calc_time": calc_time, "last_funding_rate": funding_rate})

                elif family == "book_depth":
                    if len(parts) != 4:
                        return "csv_invalid", f"invalid_column_count:{len(parts)}", raw_header, 0, None, None, []
                    ts = _parse_timestamp_ms(parts[0])
                    pct_str = parts[1].strip()
                    if not pct_str or not (pct_str.isdigit() or (pct_str.startswith("-") and pct_str[1:].isdigit())):
                        raise ValueError(f"invalid_percentage_format:{pct_str}")
                    pct = int(pct_str)
                    if pct not in BOOK_DEPTH_REQUIRED_PERCENTAGES:
                        return "csv_invalid", f"unapproved_percentage:{pct}", raw_header, 0, None, None, []
                    depth_val = _parse_finite_float(parts[2], "depth")
                    if depth_val < 0:
                        raise ValueError(f"negative_depth:{depth_val}")
                    notional_val = _parse_finite_float(parts[3], "notional")
                    if notional_val < 0:
                        raise ValueError(f"negative_notional:{notional_val}")

                    if ts not in depth_ladder_by_ts:
                        depth_ladder_by_ts[ts] = set()
                    if pct in depth_ladder_by_ts[ts]:
                        return "csv_invalid", f"duplicate_depth_percentage:{ts},{pct}", raw_header, 0, None, None, []
                    depth_ladder_by_ts[ts].add(pct)
                    parsed_rows.append({"timestamp": ts, "percentage": pct})

                elif family == "agg_trades":
                    if len(parts) != 7:
                        return "csv_invalid", f"invalid_column_count:{len(parts)}", raw_header, 0, None, None, []
                    agg_trade_id = _parse_nonnegative_int(parts[0], "agg_trade_id")
                    price_val = _parse_finite_float(parts[1], "price")
                    if price_val <= 0:
                        raise ValueError(f"non_positive_price:{price_val}")
                    qty_val = _parse_finite_float(parts[2], "quantity")
                    if qty_val < 0:
                        raise ValueError(f"negative_quantity:{qty_val}")
                    first_trade_id = _parse_nonnegative_int(parts[3], "first_trade_id")
                    last_trade_id = _parse_nonnegative_int(parts[4], "last_trade_id")
                    if last_trade_id < first_trade_id:
                        raise ValueError(f"invalid_trade_id_range:{first_trade_id}>{last_trade_id}")
                    transact_time = _parse_nonnegative_int(parts[5], "transact_time")
                    ibm_str = parts[6].strip().lower()
                    if ibm_str not in {"true", "false"}:
                        raise ValueError(f"invalid_is_buyer_maker:{parts[6]}")
                    parsed_rows.append({"agg_trade_id": agg_trade_id, "transact_time": transact_time})

            except Exception as exc:
                return "csv_invalid", f"row_parse_error:{row_idx}:{exc}", raw_header, 0, None, None, []

        # BookDepth complete ladder validation
        if family == "book_depth":
            for ts, pcts in depth_ladder_by_ts.items():
                if pcts != BOOK_DEPTH_REQUIRED_PERCENTAGES:
                    return "csv_invalid", f"incomplete_book_depth_ladder:{ts}:missing_{BOOK_DEPTH_REQUIRED_PERCENTAGES - pcts}", raw_header, 0, None, None, []

        return "fetched_verified", "ok", raw_header, len(parsed_rows), first_row_str, last_row_str, parsed_rows
    finally:
        if file_handle is not None:
            try:
                file_handle.close()
            except Exception:
                pass


def ceil_step(t: int, step_ms: int) -> int:
    """Exact ((t + step_ms - 1) // step_ms) * step_ms."""
    return ((t + step_ms - 1) // step_ms) * step_ms


def evaluate_coverage(
    metric: str,
    window: str,
    window_start_ms: int,
    window_end_ms: int,
    rows: List[Dict[str, Any]],
    canonical_symbol: str,
    fetch_status: str,
    failure_reason: str,
) -> Dict[str, Any]:
    """Evaluate Section 5.4 family coverage on parsed rows."""
    ts_key = TIMESTAMP_KEYS.get(metric, "open_time")
    step_ms = GRID_STEP_MS.get(metric)

    # Base dictionary
    cov_result: Dict[str, Any] = {
        "timestamp_key": ts_key,
        "requested_interval_start_ms": window_start_ms,
        "requested_interval_end_ms": window_end_ms,
        "expected_grid_step_ms": step_ms,
        "parsed_window_row_count": 0,
        "observed_first_timestamp_ms": None,
        "observed_last_timestamp_ms": None,
        "duplicate_count": 0,
        "conflict_count": 0,
        "gap_count": 0,
        "coverage_status": "not_proven",
        "reason": failure_reason,
    }

    if fetch_status == "archive_not_found_404":
        cov_result["coverage_status"] = "unavailable"
        cov_result["reason"] = "archive_not_found_404"
        return cov_result

    if fetch_status != "fetched_verified":
        cov_result["coverage_status"] = "not_proven"
        cov_result["reason"] = failure_reason
        return cov_result

    # Filter rows in window: window_start_ms <= timestamp < window_end_ms
    window_rows = [r for r in rows if window_start_ms <= r[ts_key] < window_end_ms]
    cov_result["parsed_window_row_count"] = len(window_rows)

    if window_rows:
        window_rows.sort(key=lambda x: x[ts_key])
        cov_result["observed_first_timestamp_ms"] = window_rows[0][ts_key]
        cov_result["observed_last_timestamp_ms"] = window_rows[-1][ts_key]

    if step_ms is not None:
        # Clock grid family (klines_1h, mark_price_1h, index_price_1h, premium_index_1h, metrics_5m)
        grid_points = list(range(ceil_step(window_start_ms, step_ms), window_end_ms, step_ms))
        expected_set = set(grid_points)

        observed_counts: Dict[int, int] = {}
        for r in window_rows:
            ts = r[ts_key]
            observed_counts[ts] = observed_counts.get(ts, 0) + 1

        duplicates = sum(cnt - 1 for cnt in observed_counts.values() if cnt > 1)
        gaps = len(expected_set - set(observed_counts.keys()))

        cov_result["duplicate_count"] = duplicates
        cov_result["conflict_count"] = duplicates
        cov_result["gap_count"] = gaps

        if gaps == 0 and duplicates == 0 and len(window_rows) == len(grid_points) and len(grid_points) > 0:
            cov_result["coverage_status"] = "window_observed"
            cov_result["reason"] = "full_grid_observed"
        else:
            cov_result["coverage_status"] = "window_incomplete"
            cov_result["reason"] = f"grid_incomplete:gaps={gaps},conflicts={duplicates}"

    else:
        # Non-grid family (funding_rate, book_depth, agg_trades)
        cov_result["gap_count"] = 0
        conflicts = 0

        if metric == "funding_rate":
            counts = {}
            for r in window_rows:
                t = r["calc_time"]
                counts[t] = counts.get(t, 0) + 1
            conflicts = sum(c - 1 for c in counts.values() if c > 1)

        elif metric == "agg_trades":
            trade_ids = {}
            for r in window_rows:
                tid = r["agg_trade_id"]
                trade_ids[tid] = trade_ids.get(tid, 0) + 1
            conflicts = sum(c - 1 for c in trade_ids.values() if c > 1)

        cov_result["duplicate_count"] = conflicts
        cov_result["conflict_count"] = conflicts

        if conflicts > 0:
            cov_result["coverage_status"] = "not_proven"
            cov_result["reason"] = f"conflict_duplicates:{conflicts}"
        elif window_rows:
            cov_result["coverage_status"] = "rows_observed_continuity_not_proven"
            cov_result["reason"] = "rows_observed"
        else:
            cov_result["coverage_status"] = "no_rows_observed"
            cov_result["reason"] = "no_rows_in_window"

    return cov_result


def fetch_and_validate_physical_object(
    url: str,
    family: str,
    canonical_symbol: str,
    fetch_callable: Optional[Callable[[str], Tuple[int, bytes, str]]] = None,
) -> Dict[str, Any]:
    """Perform single GET request and process ZIP/CSV payload."""
    start_ms = int(datetime.datetime.now(timezone.utc).timestamp() * 1000)
    res = {
        "exact_source_url": url,
        "fetch_status": "transport_inconclusive",
        "http_status_or_transport_error": None,
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
        "request_started_at_ms": start_ms,
        "response_observed_at_ms": None,
        "reason": "uninitialized",
        "zip_bytes": None,
        "csv_bytes": None,
        "parsed_rows": [],
    }

    if fetch_callable is not None:
        try:
            http_status, raw_body, err_or_status = fetch_callable(url)
            res["http_status_or_transport_error"] = http_status
            res["response_observed_at_ms"] = int(datetime.datetime.now(timezone.utc).timestamp() * 1000)
            if http_status == 404:
                res["fetch_status"] = "archive_not_found_404"
                res["reason"] = "HTTP 404 Not Found"
                return res
            elif http_status in (301, 302, 303, 307, 308):
                res["fetch_status"] = "redirect_refused"
                res["reason"] = f"HTTP redirect refused: {http_status}"
                return res
            elif http_status != 200:
                res["fetch_status"] = "transport_inconclusive"
                res["reason"] = f"HTTP error {http_status}: {err_or_status}"
                return res
            else:
                body_bytes = raw_body
        except Exception as exc:
            res["fetch_status"] = "transport_inconclusive"
            res["reason"] = f"transport_callable_exception: {exc}"
            return res
    else:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT},
        )
        opener = get_canonical_opener()
        timeout_sec = EXCHANGE_TIMEOUT_MS / 1000.0
        try:
            with opener.open(req, timeout=timeout_sec) as resp:
                res["http_status_or_transport_error"] = resp.status
                res["response_observed_at_ms"] = int(datetime.datetime.now(timezone.utc).timestamp() * 1000)
                body_bytes = resp.read()
        except urllib.error.HTTPError as exc:
            res["http_status_or_transport_error"] = exc.code
            res["response_observed_at_ms"] = int(datetime.datetime.now(timezone.utc).timestamp() * 1000)
            if exc.code == 404:
                res["fetch_status"] = "archive_not_found_404"
                res["reason"] = "HTTP 404 Not Found"
                return res
            elif exc.code in (301, 302, 303, 307, 308):
                res["fetch_status"] = "redirect_refused"
                res["reason"] = f"HTTP redirect refused: {exc.code}"
                return res
            else:
                res["fetch_status"] = "transport_inconclusive"
                res["reason"] = f"HTTP error {exc.code}"
                return res
        except (urllib.error.URLError, socket.timeout, Exception) as exc:
            res["fetch_status"] = "transport_inconclusive"
            res["reason"] = f"transport_error: {exc}"
            return res

    res["zip_bytes"] = body_bytes
    z_status, z_reason, member_name, csv_bytes = validate_zip_member(body_bytes)
    if z_status != "fetched_verified":
        res["fetch_status"] = z_status
        res["reason"] = z_reason
        return res

    res["zip_member_name"] = member_name
    res["csv_bytes"] = csv_bytes

    c_status, c_reason, header, row_count, first_row, last_row, parsed_rows = parse_and_validate_csv(
        family, csv_bytes, canonical_symbol
    )
    if c_status != "fetched_verified":
        if isinstance(csv_bytes, Path):
            try:
                csv_bytes.unlink(missing_ok=True)
            except Exception:
                pass
        res["fetch_status"] = c_status
        res["reason"] = c_reason
        return res

    res["fetch_status"] = "fetched_verified"
    res["csv_header"] = header
    res["csv_row_count"] = row_count
    res["first_row"] = first_row
    res["last_row"] = last_row
    res["parsed_rows"] = parsed_rows
    res["reason"] = "ok"
    return res


def iso_to_ms(iso_str: str) -> int:
    """Convert ISO-8601 string to UTC epoch milliseconds."""
    dt = datetime.datetime.fromisoformat(iso_str)
    return int(dt.timestamp() * 1000)


def atomic_write_bytes(target_file: Path, content: Union[bytes, Path, str]) -> str:
    """Atomically write content to target_file with statvfs check, temp write, and read-back verification."""
    target_file.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, Path):
        content_len = content.stat().st_size
    elif isinstance(content, (bytes, bytearray)):
        content_len = len(content)
    elif isinstance(content, str):
        content_len = len(content.encode("utf-8"))
    else:
        raise CandidateCollectorError(f"unsupported_content_type:{type(content)}")

    try:
        stat = os.statvfs(target_file.parent)
        avail = stat.f_bavail * stat.f_frsize
        required = 2 * content_len
        if avail < required:
            raise CandidateCollectorError(
                f"candidate_root_invalid:insufficient_disk_space:avail={avail}<required={required}"
            )
    except OSError as exc:
        raise CandidateCollectorError(f"candidate_root_invalid:statvfs_failed:{exc}") from exc

    temp_file = target_file.with_name(f"{target_file.name}.tmp")
    expected_sha_calc = hashlib.sha256()

    try:
        if isinstance(content, Path):
            with open(content, "rb") as src_f, open(temp_file, "wb") as dst_f:
                while True:
                    chunk = src_f.read(65536)
                    if not chunk:
                        break
                    expected_sha_calc.update(chunk)
                    dst_f.write(chunk)
                dst_f.flush()
                os.fsync(dst_f.fileno())
        elif isinstance(content, (bytes, bytearray)):
            expected_sha_calc.update(content)
            with open(temp_file, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
        elif isinstance(content, str):
            encoded = content.encode("utf-8")
            expected_sha_calc.update(encoded)
            with open(temp_file, "wb") as f:
                f.write(encoded)
                f.flush()
                os.fsync(f.fileno())
    except Exception as exc:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
        raise CandidateCollectorError(f"candidate_root_invalid:temp_write_failed:{exc}") from exc

    try:
        os.replace(temp_file, target_file)
    except Exception as exc:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass
        raise CandidateCollectorError(f"candidate_root_invalid:replace_failed:{exc}") from exc

    # Streamed read-back verification without loading whole file into memory
    read_len = 0
    read_sha_calc = hashlib.sha256()
    try:
        with open(target_file, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                read_len += len(chunk)
                read_sha_calc.update(chunk)
    except Exception as exc:
        raise CandidateCollectorError(f"candidate_root_invalid:readback_failed:{exc}") from exc

    if read_len != content_len:
        raise CandidateCollectorError(
            f"candidate_root_invalid:readback_length_mismatch:{read_len}!={content_len}"
        )

    actual_sha = read_sha_calc.hexdigest()
    expected_sha = expected_sha_calc.hexdigest()
    if actual_sha != expected_sha:
        raise CandidateCollectorError(
            f"candidate_root_invalid:readback_sha_mismatch:{actual_sha}!={expected_sha}"
        )

    return actual_sha


def execute_collection_run(
    project_root: Path,
    source_export: Path,
    completed_root: Path,
    coverage_matrix: Path,
    output_root: Path,
    run_id: str,
    approved_design_path: Path,
    approved_design_sha: str,
    approved_plan_path: Path,
    approved_plan_sha: str,
    network_authorization_file: Path,
    network_authorization_sha: str,
    fetch_callable: Optional[Callable[[str], Tuple[int, bytes, str]]] = None,
) -> Dict[str, Any]:
    """Execute complete collection run with manifest-last atomic persistence and independent validation."""
    gate_result = validate_prefetch_authority(
        project_root=project_root,
        source_export=source_export,
        completed_root=completed_root,
        coverage_matrix=coverage_matrix,
        approved_design_path=approved_design_path,
        approved_design_sha=approved_design_sha,
        approved_plan_path=approved_plan_path,
        approved_plan_sha=approved_plan_sha,
        network_authorization_file=network_authorization_file,
        network_authorization_sha=network_authorization_sha,
        run_id=run_id,
    )
    cohort = gate_result["cohort"]

    candidate_root = output_root / run_id
    if candidate_root.exists():
        raise CandidateCollectorError(f"STOP=candidate_run_id_collision:{candidate_root}")

    try:
        candidate_root.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise CandidateCollectorError(f"STOP=candidate_run_id_collision:{candidate_root}")

    zips_dir = candidate_root / "zips"
    csvs_dir = candidate_root / "csvs"
    zips_dir.mkdir(exist_ok=False)
    csvs_dir.mkdir(exist_ok=False)

    _, logical_records, physical_objects = enumerate_candidate_requests(
        coverage_matrix_path=coverage_matrix,
        cohort=cohort,
    )

    completed_phys_map: Dict[str, Dict[str, Any]] = {}
    in_memory_rows: Dict[str, List[Dict[str, Any]]] = {}

    for phys in physical_objects:
        pid = phys["physical_source_object_id"]
        url = phys["exact_source_url"]
        ref_logical = [rec for rec in logical_records if rec["physical_source_object_id"] == pid]
        if not ref_logical:
            raise CandidateCollectorError(f"candidate_root_invalid:unreferenced_physical_object:{pid}")
        family = ref_logical[0]["metric"]
        canonical_symbol = ref_logical[0]["canonical_symbol"]

        fetch_res = fetch_and_validate_physical_object(url, family, canonical_symbol, fetch_callable=fetch_callable)

        phys_record = {
            "physical_source_object_id": pid,
            "exact_source_url": url,
            "fetch_status": fetch_res["fetch_status"],
            "http_status_or_transport_error": fetch_res["http_status_or_transport_error"],
            "zip_relative_path": None,
            "zip_byte_length": None,
            "zip_sha256": None,
            "csv_relative_path": None,
            "csv_byte_length": None,
            "csv_sha256": None,
            "zip_member_name": fetch_res["zip_member_name"],
            "csv_header": fetch_res["csv_header"],
            "csv_row_count": fetch_res["csv_row_count"],
            "first_row": fetch_res["first_row"],
            "last_row": fetch_res["last_row"],
            "request_started_at_ms": fetch_res["request_started_at_ms"],
            "response_observed_at_ms": fetch_res["response_observed_at_ms"],
            "reason": fetch_res["reason"],
        }

        if fetch_res["zip_bytes"] is not None:
            zip_rel = f"zips/{pid}.zip"
            zip_path = candidate_root / zip_rel
            actual_zip_sha = atomic_write_bytes(zip_path, fetch_res["zip_bytes"])
            phys_record["zip_relative_path"] = zip_rel
            phys_record["zip_byte_length"] = len(fetch_res["zip_bytes"])
            phys_record["zip_sha256"] = actual_zip_sha

        if fetch_res["csv_bytes"] is not None:
            csv_rel = f"csvs/{pid}.csv"
            csv_path = candidate_root / csv_rel
            actual_csv_sha = atomic_write_bytes(csv_path, fetch_res["csv_bytes"])
            phys_record["csv_relative_path"] = csv_rel
            phys_record["csv_byte_length"] = len(fetch_res["csv_bytes"])
            phys_record["csv_sha256"] = actual_csv_sha
            if isinstance(fetch_res["csv_bytes"], Path):
                try:
                    fetch_res["csv_bytes"].unlink(missing_ok=True)
                except Exception:
                    pass

        completed_phys_map[pid] = phys_record
        in_memory_rows[pid] = fetch_res["parsed_rows"]

    # Populate logical records
    for l_rec in logical_records:
        phys_rec = completed_phys_map[l_rec["physical_source_object_id"]]
        l_rec["record_state"] = phys_rec["fetch_status"]
        l_rec["reason"] = phys_rec["reason"]

        w_start_ms = iso_to_ms(l_rec["window_start_utc"])
        w_end_ms = iso_to_ms(l_rec["window_end_utc"])
        rows = in_memory_rows[l_rec["physical_source_object_id"]]

        cov = evaluate_coverage(
            metric=l_rec["metric"],
            window=l_rec["window"],
            window_start_ms=w_start_ms,
            window_end_ms=w_end_ms,
            rows=rows,
            canonical_symbol=l_rec["canonical_symbol"],
            fetch_status=phys_rec["fetch_status"],
            failure_reason=phys_rec["reason"],
        )
        l_rec["parsed_window_row_count"] = cov["parsed_window_row_count"]
        l_rec["observed_first_timestamp_ms"] = cov["observed_first_timestamp_ms"]
        l_rec["observed_last_timestamp_ms"] = cov["observed_last_timestamp_ms"]
        l_rec["duplicate_count"] = cov["duplicate_count"]
        l_rec["conflict_count"] = cov["conflict_count"]
        l_rec["gap_count"] = cov["gap_count"]

    # Compute metric_window_coverages
    groups: Dict[Tuple[str, str, str, str, str], List[Dict[str, Any]]] = {}
    for l_rec in logical_records:
        grp_key = (
            l_rec["parent_article_id"],
            l_rec["contract_id"],
            l_rec["canonical_symbol"],
            l_rec["window"],
            l_rec["metric"],
        )
        if grp_key not in groups:
            groups[grp_key] = []
        groups[grp_key].append(l_rec)

    metric_window_coverages = []
    for grp_key in sorted(groups.keys()):
        recs = groups[grp_key]
        first_rec = recs[0]
        w_start_ms = iso_to_ms(first_rec["window_start_utc"])
        w_end_ms = iso_to_ms(first_rec["window_end_utc"])
        metric = first_rec["metric"]
        canonical_symbol = first_rec["canonical_symbol"]

        statuses = [completed_phys_map[r["physical_source_object_id"]]["fetch_status"] for r in recs]
        reasons = [completed_phys_map[r["physical_source_object_id"]]["reason"] for r in recs]

        all_404 = all(s == "archive_not_found_404" for s in statuses)
        all_verified = all(s == "fetched_verified" for s in statuses)

        if all_verified:
            joined_rows: List[Dict[str, Any]] = []
            for r in recs:
                joined_rows.extend(in_memory_rows[r["physical_source_object_id"]])
            cov = evaluate_coverage(
                metric=metric,
                window=first_rec["window"],
                window_start_ms=w_start_ms,
                window_end_ms=w_end_ms,
                rows=joined_rows,
                canonical_symbol=canonical_symbol,
                fetch_status="fetched_verified",
                failure_reason="ok",
            )
        elif all_404:
            cov = evaluate_coverage(
                metric=metric,
                window=first_rec["window"],
                window_start_ms=w_start_ms,
                window_end_ms=w_end_ms,
                rows=[],
                canonical_symbol=canonical_symbol,
                fetch_status="archive_not_found_404",
                failure_reason="archive_not_found_404",
            )
        else:
            first_err = next((r for s, r in zip(statuses, reasons) if s != "fetched_verified"), "not_proven")
            cov = evaluate_coverage(
                metric=metric,
                window=first_rec["window"],
                window_start_ms=w_start_ms,
                window_end_ms=w_end_ms,
                rows=[],
                canonical_symbol=canonical_symbol,
                fetch_status="transport_inconclusive",
                failure_reason=first_err,
            )

        coverage_entry = {
            "parent_article_id": grp_key[0],
            "contract_id": grp_key[1],
            "canonical_symbol": grp_key[2],
            "window": grp_key[3],
            "metric": grp_key[4],
            "timestamp_key": cov["timestamp_key"],
            "requested_interval_start_ms": cov["requested_interval_start_ms"],
            "requested_interval_end_ms": cov["requested_interval_end_ms"],
            "expected_grid_step_ms": cov["expected_grid_step_ms"],
            "parsed_window_row_count": cov["parsed_window_row_count"],
            "observed_first_timestamp_ms": cov["observed_first_timestamp_ms"],
            "observed_last_timestamp_ms": cov["observed_last_timestamp_ms"],
            "duplicate_count": cov["duplicate_count"],
            "conflict_count": cov["conflict_count"],
            "gap_count": cov["gap_count"],
            "coverage_status": cov["coverage_status"],
            "reason": cov["reason"],
        }
        metric_window_coverages.append(coverage_entry)

    # Derive candidate_root_state
    completed_physical_objects = [completed_phys_map[k] for k in sorted(completed_phys_map.keys())]

    grid_families = {"klines_1h", "mark_price_1h", "index_price_1h", "premium_index_1h", "metrics_5m"}
    all_phys_verified = all(p["fetch_status"] == "fetched_verified" for p in completed_physical_objects)
    all_grid_observed = all(
        c["coverage_status"] == "window_observed"
        for c in metric_window_coverages
        if c["metric"] in grid_families
    )
    all_nongrid_observed = all(
        c["coverage_status"] == "rows_observed_continuity_not_proven"
        for c in metric_window_coverages
        if c["metric"] not in grid_families
    )

    if all_phys_verified and all_grid_observed and all_nongrid_observed:
        candidate_root_state = "collection_terminal_with_full_grid_coverage"
    else:
        candidate_root_state = "collection_terminal_with_gaps_or_unproven_data"

    # Assemble authority packet
    authority_packet = {
        key: {
            "path": rel_p,
            "sha256": EXACT_AUTHORITY_FILES[key],
        }
        for rel_p, key in FIXED_AUTHORITY_KEY_MAP.items()
    }
    def _to_rel_str(p: Path) -> str:
        try:
            return str(p.resolve().relative_to(project_root.resolve()))
        except Exception:
            return str(p)

    authority_packet["approved_historical_evidence_expansion_design"] = {
        "path": _to_rel_str(approved_design_path),
        "sha256": approved_design_sha,
    }
    authority_packet["approved_expansion_implementation_plan"] = {
        "path": _to_rel_str(approved_plan_path),
        "sha256": approved_plan_sha,
    }
    authority_packet["network_collection_authorization"] = {
        "run_id": run_id,
        "approved_design_sha256": approved_design_sha,
        "approved_plan_sha256": approved_plan_sha,
        "authorization_record_sha256": network_authorization_sha,
    }

    # Verify retained files on disk before manifest publication
    for p in completed_physical_objects:
        if p["zip_relative_path"] is not None:
            zp = candidate_root / p["zip_relative_path"]
            if not zp.is_file():
                raise CandidateCollectorError(f"candidate_root_invalid:missing_retained_zip:{zp}")
            if zp.stat().st_size != p["zip_byte_length"] or compute_file_sha256(zp) != p["zip_sha256"]:
                raise CandidateCollectorError(f"candidate_root_invalid:retained_zip_corrupted:{zp}")
        if p["csv_relative_path"] is not None:
            cp = candidate_root / p["csv_relative_path"]
            if not cp.is_file():
                raise CandidateCollectorError(f"candidate_root_invalid:missing_retained_csv:{cp}")
            if cp.stat().st_size != p["csv_byte_length"] or compute_file_sha256(cp) != p["csv_sha256"]:
                raise CandidateCollectorError(f"candidate_root_invalid:retained_csv_corrupted:{cp}")

    manifest_data = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "authority_packet": authority_packet,
        "cohort": cohort,
        "physical_source_objects": completed_physical_objects,
        "logical_archive_records": logical_records,
        "metric_window_coverages": metric_window_coverages,
        "candidate_root_state": candidate_root_state,
        "capture_mode": "historical_ex_post_candidate",
        "point_in_time_source_validated": False,
        "authority_flags": EXACT_EXPECTED_13_FALSE_MAPPING,
    }
    manifest_bytes = json.dumps(manifest_data, indent=2, ensure_ascii=False).encode("utf-8")
    manifest_path = candidate_root / "candidate_manifest.json"
    atomic_write_bytes(manifest_path, manifest_bytes)

    validate_completed_candidate_root(
        completed_root=candidate_root,
        approved_design_path=approved_design_path,
        approved_design_sha=approved_design_sha,
        approved_plan_path=approved_plan_path,
        approved_plan_sha=approved_plan_sha,
        network_authorization_sha=network_authorization_sha,
        project_root=project_root,
    )

    return manifest_data


def validate_completed_candidate_root(
    completed_root: Path,
    approved_design_path: Path,
    approved_design_sha: str,
    approved_plan_path: Path,
    approved_plan_sha: str,
    network_authorization_sha: str,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Strict independent reader validating completed candidate root."""
    manifest_path = completed_root / "candidate_manifest.json"
    if not manifest_path.is_file():
        raise CandidateCollectorError("candidate_root_invalid:missing_manifest")
    if manifest_path.is_symlink():
        raise CandidateCollectorError("candidate_root_invalid:symlink_detected:candidate_manifest.json")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CandidateCollectorError(f"candidate_root_invalid:corrupted_manifest_json:{exc}") from exc

    if not isinstance(manifest, dict):
        raise CandidateCollectorError("candidate_root_invalid:manifest_not_dict")

    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise CandidateCollectorError(f"candidate_root_invalid:schema_version_mismatch:{manifest.get('schema_version')}")

    if set(manifest.keys()) != EXPECTED_11_MANIFEST_KEYS:
        raise CandidateCollectorError("candidate_root_invalid:manifest_keys_mismatch")

    if manifest["run_id"] != completed_root.name:
        raise CandidateCollectorError(
            f"candidate_root_invalid:run_id_mismatch:{manifest['run_id']}!={completed_root.name}"
        )

    flags = manifest["authority_flags"]
    if not isinstance(flags, dict) or set(flags.keys()) != set(EXACT_EXPECTED_13_FALSE_MAPPING.keys()):
        raise CandidateCollectorError("candidate_root_invalid:authority_flags_keys_mismatch")
    for k, v in flags.items():
        if v is not False:
            raise CandidateCollectorError(f"candidate_root_invalid:authority_flag_not_false:{k}={v}")

    if manifest["capture_mode"] != "historical_ex_post_candidate":
        raise CandidateCollectorError(f"candidate_root_invalid:capture_mode_mismatch:{manifest['capture_mode']}")

    if manifest["point_in_time_source_validated"] is not False:
        raise CandidateCollectorError("candidate_root_invalid:point_in_time_source_validated_must_be_false")

    auth_pkt = manifest["authority_packet"]
    if not isinstance(auth_pkt, dict) or set(auth_pkt.keys()) != EXPECTED_13_AUTHORITY_PACKET_KEYS:
        raise CandidateCollectorError("candidate_root_invalid:authority_packet_keys_mismatch")

    if auth_pkt["approved_historical_evidence_expansion_design"]["sha256"] != approved_design_sha:
        raise CandidateCollectorError("candidate_root_invalid:approved_design_sha_mismatch")
    if auth_pkt["approved_expansion_implementation_plan"]["sha256"] != approved_plan_sha:
        raise CandidateCollectorError("candidate_root_invalid:approved_plan_sha_mismatch")

    net_auth = auth_pkt["network_collection_authorization"]
    if net_auth["run_id"] != manifest["run_id"]:
        raise CandidateCollectorError("candidate_root_invalid:network_auth_run_id_mismatch")
    if net_auth["approved_design_sha256"] != approved_design_sha:
        raise CandidateCollectorError("candidate_root_invalid:network_auth_design_sha_mismatch")
    if net_auth["approved_plan_sha256"] != approved_plan_sha:
        raise CandidateCollectorError("candidate_root_invalid:network_auth_plan_sha_mismatch")
    if net_auth["authorization_record_sha256"] != network_authorization_sha:
        raise CandidateCollectorError("candidate_root_invalid:network_auth_record_sha_mismatch")

    root_dir = project_root if project_root is not None else Path(".").resolve()
    for rel_p, key in FIXED_AUTHORITY_KEY_MAP.items():
        exp_sha = EXACT_AUTHORITY_FILES[key]
        if auth_pkt[key]["sha256"] != exp_sha:
            raise CandidateCollectorError(f"candidate_root_invalid:authority_packet_sha_mismatch:{key}")
        disk_p = root_dir / rel_p
        if not disk_p.is_file():
            raise CandidateCollectorError(f"candidate_root_invalid:missing_workspace_authority:{rel_p}")
        actual_sha = compute_file_sha256(disk_p)
        if actual_sha != exp_sha:
            raise CandidateCollectorError(f"candidate_root_invalid:workspace_authority_mismatch:{rel_p}")

    # Re-verify cohort from canonical C input
    c_comp_path = root_dir / "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json"
    matrix_p = root_dir / "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json"
    if not c_comp_path.is_file():
        raise CandidateCollectorError(f"candidate_root_invalid:missing_workspace_authority:{c_comp_path}")
    if not matrix_p.is_file():
        raise CandidateCollectorError(f"candidate_root_invalid:missing_workspace_authority:{matrix_p}")

    c_completed = c_comp_path.parent
    b_export = root_dir / "data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090"
    if not b_export.is_dir():
        raise CandidateCollectorError(f"candidate_root_invalid:missing_workspace_authority:{b_export}")
    verified_c = verify_c_input(project_root=root_dir, completed_root=c_completed, source_export=b_export)
    expected_cohort = derive_candidate_cohort(verified_c, matrix_p)
    if manifest["cohort"] != expected_cohort:
        raise CandidateCollectorError("candidate_root_invalid:cohort_mismatch")
    if len(manifest["cohort"]) != 41:
        raise CandidateCollectorError("candidate_root_invalid:cohort_length_not_41")

    # Re-verify logical records and physical objects against frozen matrix
    _, exp_logical, exp_physical = enumerate_candidate_requests(
        coverage_matrix_path=matrix_p,
        cohort=manifest["cohort"],
    )
    if len(manifest["logical_archive_records"]) != len(exp_logical):
        raise CandidateCollectorError(
            f"candidate_root_invalid:logical_records_count_mismatch:{len(manifest['logical_archive_records'])}!={len(exp_logical)}"
        )
    if len(manifest["physical_source_objects"]) != len(exp_physical):
        raise CandidateCollectorError(
            f"candidate_root_invalid:physical_objects_count_mismatch:{len(manifest['physical_source_objects'])}!={len(exp_physical)}"
        )

    exp_log_map = {r["logical_archive_record_id"]: r for r in exp_logical}
    for log_rec in manifest["logical_archive_records"]:
        l_keys = set(log_rec.keys())
        if l_keys != EXPECTED_LOGICAL_RECORD_KEYS:
            missing = EXPECTED_LOGICAL_RECORD_KEYS - l_keys
            extra = l_keys - EXPECTED_LOGICAL_RECORD_KEYS
            raise CandidateCollectorError(
                f"candidate_root_invalid:logical_record_keys_mismatch:missing={missing},extra={extra}"
            )
        lid = log_rec["logical_archive_record_id"]
        if lid not in exp_log_map:
            raise CandidateCollectorError(f"candidate_root_invalid:unexpected_logical_record_id:{lid}")
        exp_rec = exp_log_map[lid]
        if log_rec["matrix_record_sha256"] != exp_rec["matrix_record_sha256"]:
            raise CandidateCollectorError(f"candidate_root_invalid:matrix_record_sha_mismatch:{lid}")
        if log_rec["matrix_record_projection_v1"] != exp_rec["matrix_record_projection_v1"]:
            raise CandidateCollectorError(f"candidate_root_invalid:matrix_record_projection_mismatch:{lid}")
        if log_rec["physical_source_object_id"] != exp_rec["physical_source_object_id"]:
            raise CandidateCollectorError(f"candidate_root_invalid:logical_physical_id_mismatch:{lid}")
        if log_rec["exact_source_url"] != exp_rec["exact_source_url"]:
            raise CandidateCollectorError(f"candidate_root_invalid:logical_exact_source_url_mismatch:{lid}")
        if log_rec["coverage_matrix_sha256"] != exp_rec["coverage_matrix_sha256"]:
            raise CandidateCollectorError(f"candidate_root_invalid:logical_matrix_sha_mismatch:{lid}")

    exp_phys_map = {p["physical_source_object_id"]: p for p in exp_physical}
    for p in manifest["physical_source_objects"]:
        p_keys = set(p.keys())
        if p_keys != EXPECTED_PHYSICAL_OBJECT_KEYS:
            missing = EXPECTED_PHYSICAL_OBJECT_KEYS - p_keys
            extra = p_keys - EXPECTED_PHYSICAL_OBJECT_KEYS
            raise CandidateCollectorError(
                f"candidate_root_invalid:physical_object_keys_mismatch:missing={missing},extra={extra}"
            )
        pid = p["physical_source_object_id"]
        if pid not in exp_phys_map:
            raise CandidateCollectorError(f"candidate_root_invalid:unexpected_physical_source_object_id:{pid}")
        exp_p = exp_phys_map[pid]
        if p["exact_source_url"] != exp_p["exact_source_url"]:
            raise CandidateCollectorError(
                f"candidate_root_invalid:exact_source_url_mismatch:{pid}:{p['exact_source_url']}!={exp_p['exact_source_url']}"
            )
        derived_pid = compute_physical_source_object_id(p["exact_source_url"])
        if derived_pid != pid:
            raise CandidateCollectorError(
                f"candidate_root_invalid:physical_id_url_hash_mismatch:{pid}!={derived_pid}"
            )

    for cov_entry in manifest["metric_window_coverages"]:
        c_keys = set(cov_entry.keys())
        if c_keys != EXPECTED_METRIC_WINDOW_COVERAGE_KEYS:
            missing = EXPECTED_METRIC_WINDOW_COVERAGE_KEYS - c_keys
            extra = c_keys - EXPECTED_METRIC_WINDOW_COVERAGE_KEYS
            raise CandidateCollectorError(
                f"candidate_root_invalid:metric_window_coverage_keys_mismatch:missing={missing},extra={extra}"
            )

    # Verify terminal status enumerations
    allowed_terminal_statuses = {
        "fetched_verified",
        "archive_not_found_404",
        "redirect_refused",
        "transport_inconclusive",
        "archive_invalid",
        "csv_invalid",
    }
    phys_status_map: Dict[str, str] = {}
    for p in manifest["physical_source_objects"]:
        st = p.get("fetch_status")
        if st not in allowed_terminal_statuses:
            raise CandidateCollectorError(f"candidate_root_invalid:illegal_physical_fetch_status:{st}")
        phys_status_map[p["physical_source_object_id"]] = st

    for log_rec in manifest["logical_archive_records"]:
        st = log_rec.get("record_state")
        if st not in allowed_terminal_statuses:
            raise CandidateCollectorError(f"candidate_root_invalid:illegal_logical_record_state:{st}")
        pid = log_rec["physical_source_object_id"]
        if st != phys_status_map.get(pid):
            raise CandidateCollectorError(
                f"candidate_root_invalid:record_state_mismatch_with_physical:{st}!={phys_status_map.get(pid)}"
            )

    # Verify on-disk file tree, symlinks, temp files, and contents
    declared_files = {"candidate_manifest.json"}
    for p in manifest["physical_source_objects"]:
        if p["zip_relative_path"] is not None:
            declared_files.add(p["zip_relative_path"])
        if p["csv_relative_path"] is not None:
            declared_files.add(p["csv_relative_path"])

    for item in completed_root.rglob("*"):
        if item.is_symlink():
            raise CandidateCollectorError(f"candidate_root_invalid:symlink_detected:{item}")
        if item.is_file():
            rel = str(item.relative_to(completed_root))
            if rel.endswith(".tmp") or ".tmp." in rel:
                raise CandidateCollectorError(f"candidate_root_invalid:stale_temp_file:{rel}")
            if rel not in declared_files:
                raise CandidateCollectorError(f"candidate_root_invalid:unexpected_file:{rel}")
        elif item.is_dir():
            rel = str(item.relative_to(completed_root))
            if rel not in ("zips", "csvs"):
                raise CandidateCollectorError(f"candidate_root_invalid:unexpected_dir:{rel}")

    seen_phys_ids = set()
    seen_zip_paths = set()
    seen_csv_paths = set()
    for p in manifest["physical_source_objects"]:
        pid = p["physical_source_object_id"]
        if pid in seen_phys_ids:
            raise CandidateCollectorError(f"candidate_root_invalid:duplicate_physical_id:{pid}")
        seen_phys_ids.add(pid)

        z_rel = p["zip_relative_path"]
        if z_rel is not None:
            if z_rel in seen_zip_paths:
                raise CandidateCollectorError(f"candidate_root_invalid:duplicate_zip_path:{z_rel}")
            seen_zip_paths.add(z_rel)
            z_path = completed_root / z_rel
            if not z_path.is_file():
                raise CandidateCollectorError(f"candidate_root_invalid:missing_zip_file:{z_rel}")
            if z_path.stat().st_size != p["zip_byte_length"]:
                raise CandidateCollectorError(f"candidate_root_invalid:zip_length_mismatch:{z_rel}")
            if compute_file_sha256(z_path) != p["zip_sha256"]:
                raise CandidateCollectorError(f"candidate_root_invalid:zip_sha_mismatch:{z_rel}")

        c_rel = p["csv_relative_path"]
        if c_rel is not None:
            if c_rel in seen_csv_paths:
                raise CandidateCollectorError(f"candidate_root_invalid:duplicate_csv_path:{c_rel}")
            seen_csv_paths.add(c_rel)
            c_path = completed_root / c_rel
            if not c_path.is_file():
                raise CandidateCollectorError(f"candidate_root_invalid:missing_csv_file:{c_rel}")
            if c_path.stat().st_size != p["csv_byte_length"]:
                raise CandidateCollectorError(f"candidate_root_invalid:csv_length_mismatch:{c_rel}")
            if compute_file_sha256(c_path) != p["csv_sha256"]:
                raise CandidateCollectorError(f"candidate_root_invalid:csv_sha_mismatch:{c_rel}")

    # Re-read and re-parse CSV files from disk for all verified physical objects
    recomputed_in_memory_rows: Dict[str, List[Dict[str, Any]]] = {}
    for p in manifest["physical_source_objects"]:
        pid = p["physical_source_object_id"]
        c_rel = p["csv_relative_path"]
        if p["fetch_status"] == "fetched_verified":
            if c_rel is None:
                raise CandidateCollectorError(f"candidate_root_invalid:missing_csv_path_for_verified_object:{pid}")
            c_path = completed_root / c_rel
            if not c_path.is_file():
                raise CandidateCollectorError(f"candidate_root_invalid:missing_csv_file:{c_rel}")

            ref_logical = [r for r in manifest["logical_archive_records"] if r["physical_source_object_id"] == pid]
            if not ref_logical:
                raise CandidateCollectorError(f"candidate_root_invalid:unreferenced_physical_id:{pid}")
            family = ref_logical[0]["metric"]
            symbol = ref_logical[0]["canonical_symbol"]

            c_status, c_reason, raw_header, row_cnt, first_r, last_r, parsed_rows = parse_and_validate_csv(
                family=family,
                csv_source=c_path,
                expected_symbol=symbol,
            )
            if c_status != "fetched_verified":
                raise CandidateCollectorError(f"candidate_root_invalid:csv_revalidation_failed:{pid}:{c_reason}")
            if row_cnt != p["csv_row_count"]:
                raise CandidateCollectorError(
                    f"candidate_root_invalid:row_count_mismatch:{pid}:{row_cnt}!={p['csv_row_count']}"
                )
            if first_r != p["first_row"]:
                raise CandidateCollectorError(f"candidate_root_invalid:first_row_mismatch:{pid}")
            if last_r != p["last_row"]:
                raise CandidateCollectorError(f"candidate_root_invalid:last_row_mismatch:{pid}")
            recomputed_in_memory_rows[pid] = parsed_rows
        else:
            recomputed_in_memory_rows[pid] = []

    # Recompute metric_window_coverages independently
    phys_records_map = {p["physical_source_object_id"]: p for p in manifest["physical_source_objects"]}
    recomputed_coverages: List[Dict[str, Any]] = []
    val_groups: Dict[Tuple[str, str, str, str, str], List[Dict[str, Any]]] = {}
    for l_rec in manifest["logical_archive_records"]:
        grp_key = (
            l_rec["parent_article_id"],
            l_rec["contract_id"],
            l_rec["canonical_symbol"],
            l_rec["window"],
            l_rec["metric"],
        )
        if grp_key not in val_groups:
            val_groups[grp_key] = []
        val_groups[grp_key].append(l_rec)

    for grp_key in sorted(val_groups.keys()):
        recs = val_groups[grp_key]
        first_rec = recs[0]
        w_start_ms = iso_to_ms(first_rec["window_start_utc"])
        w_end_ms = iso_to_ms(first_rec["window_end_utc"])
        metric = first_rec["metric"]
        canonical_symbol = first_rec["canonical_symbol"]

        statuses = [phys_records_map[r["physical_source_object_id"]]["fetch_status"] for r in recs]
        reasons = [phys_records_map[r["physical_source_object_id"]]["reason"] for r in recs]

        all_404 = all(s == "archive_not_found_404" for s in statuses)
        all_verified = all(s == "fetched_verified" for s in statuses)

        if all_verified:
            joined_rows: List[Dict[str, Any]] = []
            for r in recs:
                joined_rows.extend(recomputed_in_memory_rows[r["physical_source_object_id"]])
            cov = evaluate_coverage(
                metric=metric,
                window=first_rec["window"],
                window_start_ms=w_start_ms,
                window_end_ms=w_end_ms,
                rows=joined_rows,
                canonical_symbol=canonical_symbol,
                fetch_status="fetched_verified",
                failure_reason="ok",
            )
        elif all_404:
            cov = evaluate_coverage(
                metric=metric,
                window=first_rec["window"],
                window_start_ms=w_start_ms,
                window_end_ms=w_end_ms,
                rows=[],
                canonical_symbol=canonical_symbol,
                fetch_status="archive_not_found_404",
                failure_reason="archive_not_found_404",
            )
        else:
            first_err = next((r for s, r in zip(statuses, reasons) if s != "fetched_verified"), "not_proven")
            cov = evaluate_coverage(
                metric=metric,
                window=first_rec["window"],
                window_start_ms=w_start_ms,
                window_end_ms=w_end_ms,
                rows=[],
                canonical_symbol=canonical_symbol,
                fetch_status="transport_inconclusive",
                failure_reason=first_err,
            )

        coverage_entry = {
            "parent_article_id": grp_key[0],
            "contract_id": grp_key[1],
            "canonical_symbol": grp_key[2],
            "window": grp_key[3],
            "metric": grp_key[4],
            "timestamp_key": cov["timestamp_key"],
            "requested_interval_start_ms": cov["requested_interval_start_ms"],
            "requested_interval_end_ms": cov["requested_interval_end_ms"],
            "expected_grid_step_ms": cov["expected_grid_step_ms"],
            "parsed_window_row_count": cov["parsed_window_row_count"],
            "observed_first_timestamp_ms": cov["observed_first_timestamp_ms"],
            "observed_last_timestamp_ms": cov["observed_last_timestamp_ms"],
            "duplicate_count": cov["duplicate_count"],
            "conflict_count": cov["conflict_count"],
            "gap_count": cov["gap_count"],
            "coverage_status": cov["coverage_status"],
            "reason": cov["reason"],
        }
        recomputed_coverages.append(coverage_entry)

    if len(recomputed_coverages) != len(manifest["metric_window_coverages"]):
        raise CandidateCollectorError(
            f"candidate_root_invalid:coverages_count_mismatch:{len(recomputed_coverages)}!={len(manifest['metric_window_coverages'])}"
        )
    for idx, (exp_c, act_c) in enumerate(zip(recomputed_coverages, manifest["metric_window_coverages"])):
        if exp_c != act_c:
            raise CandidateCollectorError(
                f"candidate_root_invalid:coverage_entry_mismatch:index_{idx}"
            )

    # Re-verify candidate_root_state
    grid_families = {"klines_1h", "mark_price_1h", "index_price_1h", "premium_index_1h", "metrics_5m"}
    all_phys_verified = all(p["fetch_status"] == "fetched_verified" for p in manifest["physical_source_objects"])
    all_grid_observed = all(
        c["coverage_status"] == "window_observed"
        for c in recomputed_coverages
        if c["metric"] in grid_families
    )
    all_nongrid_observed = all(
        c["coverage_status"] == "rows_observed_continuity_not_proven"
        for c in recomputed_coverages
        if c["metric"] not in grid_families
    )
    if all_phys_verified and all_grid_observed and all_nongrid_observed:
        expected_state = "collection_terminal_with_full_grid_coverage"
    else:
        expected_state = "collection_terminal_with_gaps_or_unproven_data"

    if manifest["candidate_root_state"] != expected_state:
        raise CandidateCollectorError(
            f"candidate_root_invalid:root_state_mismatch:{manifest['candidate_root_state']}!={expected_state}"
        )

    return manifest


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Stage 1.6F historical archive collector")
    parser.add_argument("--project-root", type=Path, default=Path(".").resolve())
    parser.add_argument("--source-export", type=Path, required=True)
    parser.add_argument("--completed-root", type=Path, required=True)
    parser.add_argument("--coverage-matrix", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    parser.add_argument("--approved-design-path", type=Path, required=True)
    parser.add_argument("--approved-design-sha256", type=str, required=True)
    parser.add_argument("--approved-plan-path", type=Path, required=True)
    parser.add_argument("--approved-plan-sha256", type=str, required=True)
    parser.add_argument("--network-authorization-file", type=Path, required=True)
    parser.add_argument("--network-authorization-sha256", type=str, required=True)
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    args = parse_args(argv)
    execute_collection_run(
        project_root=args.project_root,
        source_export=args.source_export,
        completed_root=args.completed_root,
        coverage_matrix=args.coverage_matrix,
        output_root=args.output_root,
        run_id=args.run_id,
        approved_design_path=args.approved_design_path,
        approved_design_sha=args.approved_design_sha256,
        approved_plan_path=args.approved_plan_path,
        approved_plan_sha=args.approved_plan_sha256,
        network_authorization_file=args.network_authorization_file,
        network_authorization_sha=args.network_authorization_sha256,
        fetch_callable=None,
    )
    validated = validate_completed_candidate_root(
        completed_root=args.output_root / args.run_id,
        approved_design_path=args.approved_design_path,
        approved_design_sha=args.approved_design_sha256,
        approved_plan_path=args.approved_plan_path,
        approved_plan_sha=args.approved_plan_sha256,
        network_authorization_sha=args.network_authorization_sha256,
        project_root=args.project_root,
    )
    print(
        f"Collection completed and validated: run_id={args.run_id} "
        f"candidate_root_state={validated['candidate_root_state']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
