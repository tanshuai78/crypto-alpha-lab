"""Stage 1.6F candidate evidence source and strict loader core.

Invariants: INV-CA01, INV-CA02, INV-CA03, INV-CA11, INV-CA12.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple, Union

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    reconstruct_denominator,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    VerifiedCInput,
    parse_delisting_notices,
    parse_parent_audit_outcomes,
    verify_c_input,
)


class CandidateEvidenceSourceError(Exception):
    """Exception raised when candidate evidence fails validation or admission."""
    pass


SCHEMA_VERSION = "stage1_6f_historical_evidence_expansion_candidate_manifest_v1"

CANONICAL_CANDIDATE_PARENT_REL = Path("data/external_signal_shadow/stage1_6f/evidence_candidates")
CANONICAL_CANDIDATE_RUN_ID = "expansion_candidate_run_20260917_002"
CANONICAL_CANDIDATE_RELATIVE_PATH = "data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002"
CANONICAL_CANDIDATE_MANIFEST_SHA256 = "b497d5adc41a55d2a2086042ce39e5ce536686e463c722a5902f9c49a9dded67"
FROZEN_NETWORK_AUTH_RELATIVE_PATH = "configs/authorizations/network_auth_expansion_run_20260917_002.json"
FROZEN_NETWORK_AUTH_SHA256 = "8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6"

EXPECTED_11_MANIFEST_KEYS = {
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

EXACT_EXPECTED_13_FALSE_MAPPING = {
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

EXPECTED_METRIC_WINDOW_COVERAGE_KEYS = {
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

EXACT_CSV_HEADERS = {
    "klines_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "mark_price_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "index_price_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "premium_index_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "metrics_5m": "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio",
    "funding_rate": "calc_time,funding_interval_hours,last_funding_rate",
    "book_depth": "timestamp,percentage,depth,notional",
    "agg_trades": "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
}

BOOK_DEPTH_REQUIRED_PERCENTAGES = {-5, -4, -3, -2, -1, 1, 2, 3, 4, 5}

GRID_STEP_MS: Dict[str, int] = {
    "klines_1h": 3_600_000,
    "mark_price_1h": 3_600_000,
    "index_price_1h": 3_600_000,
    "premium_index_1h": 3_600_000,
    "metrics_5m": 300_000,
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


@dataclass(frozen=True)
class CandidateIdentity:
    parent_article_id: str
    contract_id: str
    canonical_symbol: str


@dataclass(frozen=True)
class PublicationAuthority:
    parent_article_id: str
    contract_id: str
    canonical_symbol: str
    t_pub_ms: int
    publication_time_authority: str


@dataclass(frozen=True)
class VerifiedCandidateEvidence:
    run_id: str
    completed_root: Path
    manifest: Dict[str, Any]
    cohort: List[str]
    physical_source_objects: List[Dict[str, Any]]
    logical_archive_records: List[Dict[str, Any]]
    metric_window_coverages: List[Dict[str, Any]]
    candidate_root_state: str
    authority_packet: Dict[str, Any]
    authority_flags: Dict[str, bool]
    parsed_series: Mapping[Tuple[str, str, str, str], List[Dict[str, Any]]]

    @property
    def candidate_root_relative_path(self) -> str:
        return CANONICAL_CANDIDATE_RELATIVE_PATH

    @property
    def manifest_sha256(self) -> str:
        return CANONICAL_CANDIDATE_MANIFEST_SHA256

    @property
    def root_state(self) -> str:
        return self.candidate_root_state


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 of file in 64k chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
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


def ceil_step(value: int, step_ms: int) -> int:
    return ((value + step_ms - 1) // step_ms) * step_ms


def iso_to_ms(iso_str: str) -> int:
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def _parse_nonnegative_int(val_str: str, field_name: str) -> int:
    v = int(val_str.strip())
    if v < 0:
        raise ValueError(f"negative_{field_name}:{v}")
    return v


def _parse_finite_float(val_str: str, field_name: str) -> float:
    f = float(val_str.strip())
    if not math.isfinite(f):
        raise ValueError(f"non_finite_{field_name}:{val_str}")
    return f


def _parse_timestamp_ms(raw_val: str) -> int:
    """Parse integer ms or YYYY-MM-DD HH:MM:SS string to epoch ms."""
    s = raw_val.strip()
    if s.isdigit():
        return int(s)
    if s.startswith("-") and s[1:].isdigit():
        raise ValueError(f"negative_timestamp:{s}")
    dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


CANONICAL_CANDIDATE_PARENT_PARTS = ("data", "external_signal_shadow", "stage1_6f", "evidence_candidates")


def validate_canonical_parent_path(
    parent_path: Path,
    project_root: Optional[Path] = None,
    is_collector: bool = False,
) -> None:
    """Strict canonical path gate matching Design line 295 / Plan line 349."""
    resolved_parent = parent_path.resolve()
    parts = resolved_parent.parts
    if len(parts) < 4 or parts[-4:] != CANONICAL_CANDIDATE_PARENT_PARTS:
        msg = f"parent_must_end_with_{'/'.join(CANONICAL_CANDIDATE_PARENT_PARTS)}:got={parent_path}"
        if is_collector:
            raise CandidateEvidenceSourceError(f"STOP=invalid_canonical_candidate_root_path:{msg}")
        else:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:non_canonical_parent_path:{msg}")

    if project_root is not None:
        resolved_proj = project_root.resolve()
        if resolved_parent.is_relative_to(resolved_proj):
            expected_canonical = (resolved_proj / CANONICAL_CANDIDATE_PARENT_REL).resolve()
            if resolved_parent != expected_canonical:
                msg = f"inside_project_must_equal_{CANONICAL_CANDIDATE_PARENT_REL}:got={resolved_parent.relative_to(resolved_proj)}"
                if is_collector:
                    raise CandidateEvidenceSourceError(f"STOP=invalid_canonical_candidate_root_path:{msg}")
                else:
                    raise CandidateEvidenceSourceError(f"candidate_root_invalid:non_canonical_parent_path:{msg}")


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
        raise CandidateEvidenceSourceError(
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

                    parsed_rows.append({
                        "open_time": open_time,
                        "open": open_p,
                        "high": high_p,
                        "low": low_p,
                        "close": close_p,
                        "volume": vol,
                        "close_time": close_time,
                        "quote_volume": quote_vol,
                        "count": count,
                        "taker_buy_volume": tb_vol,
                        "taker_buy_quote_volume": tb_quote_vol,
                    })

                elif family == "metrics_5m":
                    if len(parts) != 8:
                        return "csv_invalid", f"invalid_column_count:{len(parts)}", raw_header, 0, None, None, []
                    symbol = parts[1].strip()
                    if not symbol:
                        raise ValueError("empty_symbol")
                    if expected_symbol is not None and symbol != expected_symbol:
                        return "csv_invalid", f"symbol_mismatch:{symbol}!={expected_symbol}", raw_header, 0, None, None, []
                    create_time = _parse_timestamp_ms(parts[0])
                    sum_oi = _parse_finite_float(parts[2], "sum_open_interest")
                    sum_oi_v = _parse_finite_float(parts[3], "sum_open_interest_value")
                    count_tt_ls = _parse_finite_float(parts[4], "count_toptrader_long_short_ratio")
                    sum_tt_ls = _parse_finite_float(parts[5], "sum_toptrader_long_short_ratio")
                    count_ls = _parse_finite_float(parts[6], "count_long_short_ratio")
                    sum_taker_ls = _parse_finite_float(parts[7], "sum_taker_long_short_vol_ratio")
                    parsed_rows.append({
                        "create_time": create_time,
                        "symbol": symbol,
                        "sum_open_interest": sum_oi,
                        "sum_open_interest_value": sum_oi_v,
                        "count_toptrader_long_short_ratio": count_tt_ls,
                        "sum_toptrader_long_short_ratio": sum_tt_ls,
                        "count_long_short_ratio": count_ls,
                        "sum_taker_long_short_vol_ratio": sum_taker_ls,
                    })

                elif family == "funding_rate":
                    if len(parts) != 3:
                        return "csv_invalid", f"invalid_column_count:{len(parts)}", raw_header, 0, None, None, []
                    calc_time = _parse_nonnegative_int(parts[0], "calc_time")
                    funding_interval = _parse_finite_float(parts[1], "funding_interval_hours")
                    if funding_interval <= 0:
                        raise ValueError(f"invalid_funding_interval:{funding_interval}")
                    funding_rate = _parse_finite_float(parts[2], "last_funding_rate")
                    parsed_rows.append({
                        "calc_time": calc_time,
                        "funding_interval_hours": funding_interval,
                        "last_funding_rate": funding_rate,
                    })

                elif family == "book_depth":
                    if len(parts) != 4:
                        return "csv_invalid", f"invalid_column_count:{len(parts)}", raw_header, 0, None, None, []
                    ts = _parse_timestamp_ms(parts[0])
                    pct_str = parts[1].strip()
                    pct_f = _parse_finite_float(pct_str, "percentage")
                    if not pct_f.is_integer():
                        raise ValueError(f"non_integer_percentage:{pct_str}")
                    pct = int(pct_f)
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
                    parsed_rows.append({
                        "timestamp": ts,
                        "percentage": pct,
                        "depth": depth_val,
                        "notional": notional_val,
                    })

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
                    is_buyer_maker = (ibm_str == "true")
                    parsed_rows.append({
                        "agg_trade_id": agg_trade_id,
                        "price": price_val,
                        "quantity": qty_val,
                        "first_trade_id": first_trade_id,
                        "last_trade_id": last_trade_id,
                        "transact_time": transact_time,
                        "is_buyer_maker": is_buyer_maker,
                    })

            except Exception as exc:
                return "csv_invalid", f"row_parse_error:{row_idx}:{exc}", raw_header, 0, None, None, []

        if family == "book_depth":
            for ts, pcts in depth_ladder_by_ts.items():
                if pcts != BOOK_DEPTH_REQUIRED_PERCENTAGES:
                    return "csv_invalid", f"incomplete_book_depth_ladder:{ts}:missing_{BOOK_DEPTH_REQUIRED_PERCENTAGES - pcts}", raw_header, 0, None, None, []

        return "fetched_verified", "ok", raw_header, len(parsed_rows), first_row_str, last_row_str, parsed_rows
    finally:
        if file_handle is not None:
            file_handle.close()


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

    window_rows = [r for r in rows if window_start_ms <= r[ts_key] < window_end_ms]
    cov_result["parsed_window_row_count"] = len(window_rows)

    if window_rows:
        window_rows.sort(key=lambda x: x[ts_key])
        cov_result["observed_first_timestamp_ms"] = window_rows[0][ts_key]
        cov_result["observed_last_timestamp_ms"] = window_rows[-1][ts_key]

    if step_ms is not None:
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
            counts: Dict[Any, int] = {}
            for r in window_rows:
                t = r["calc_time"]
                counts[t] = counts.get(t, 0) + 1
            conflicts = sum(c - 1 for c in counts.values() if c > 1)

        elif metric == "agg_trades":
            trade_ids: Dict[Any, int] = {}
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


def validate_candidate_root_core(
    *,
    completed_root: Path,
    approved_design_path: Path,
    approved_design_sha: str,
    approved_plan_path: Path,
    approved_plan_sha: str,
    network_authorization_path: Path,
    network_authorization_sha: str,
    project_root: Path,
) -> VerifiedCandidateEvidence:
    """Generic shared validation core for completed candidate roots."""
    validate_canonical_parent_path(completed_root.parent, project_root=project_root, is_collector=False)
    manifest_path = completed_root / "candidate_manifest.json"
    if not manifest_path.is_file():
        raise CandidateEvidenceSourceError("candidate_root_invalid:missing_manifest")
    if manifest_path.is_symlink():
        raise CandidateEvidenceSourceError("candidate_root_invalid:symlink_detected:candidate_manifest.json")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:corrupted_manifest_json:{exc}") from exc

    if not isinstance(manifest, dict):
        raise CandidateEvidenceSourceError("candidate_root_invalid:manifest_not_dict")

    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:schema_version_mismatch:{manifest.get('schema_version')}")

    if set(manifest.keys()) != EXPECTED_11_MANIFEST_KEYS:
        raise CandidateEvidenceSourceError("candidate_root_invalid:manifest_keys_mismatch")

    if manifest["run_id"] != completed_root.name:
        raise CandidateEvidenceSourceError(
            f"candidate_root_invalid:run_id_mismatch:{manifest['run_id']}!={completed_root.name}"
        )

    flags = manifest["authority_flags"]
    if not isinstance(flags, dict) or set(flags.keys()) != set(EXACT_EXPECTED_13_FALSE_MAPPING.keys()):
        raise CandidateEvidenceSourceError("candidate_root_invalid:authority_flags_keys_mismatch")
    for k, v in flags.items():
        if v is not False:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:authority_flag_not_false:{k}={v}")

    if manifest["capture_mode"] != "historical_ex_post_candidate":
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:capture_mode_mismatch:{manifest['capture_mode']}")

    if manifest["point_in_time_source_validated"] is not False:
        raise CandidateEvidenceSourceError("candidate_root_invalid:point_in_time_source_validated_must_be_false")

    auth_pkt = manifest["authority_packet"]
    if not isinstance(auth_pkt, dict) or set(auth_pkt.keys()) != EXPECTED_13_AUTHORITY_PACKET_KEYS:
        raise CandidateEvidenceSourceError("candidate_root_invalid:authority_packet_keys_mismatch")

    if auth_pkt["approved_historical_evidence_expansion_design"]["sha256"] != approved_design_sha:
        raise CandidateEvidenceSourceError("candidate_root_invalid:approved_design_sha_mismatch")
    if auth_pkt["approved_expansion_implementation_plan"]["sha256"] != approved_plan_sha:
        raise CandidateEvidenceSourceError("candidate_root_invalid:approved_plan_sha_mismatch")

    net_auth = auth_pkt["network_collection_authorization"]
    if net_auth["run_id"] != manifest["run_id"]:
        raise CandidateEvidenceSourceError("candidate_root_invalid:network_auth_run_id_mismatch")
    if net_auth["approved_design_sha256"] != approved_design_sha:
        raise CandidateEvidenceSourceError("candidate_root_invalid:network_auth_design_sha_mismatch")
    if net_auth["approved_plan_sha256"] != approved_plan_sha:
        raise CandidateEvidenceSourceError("candidate_root_invalid:network_auth_plan_sha_mismatch")
    if net_auth["authorization_record_sha256"] != network_authorization_sha:
        raise CandidateEvidenceSourceError("candidate_root_invalid:network_auth_record_sha_mismatch")

    root_dir = project_root.resolve()

    # Verify approved expansion design file on disk
    if approved_design_path.is_symlink():
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:symlink_detected:{approved_design_path}")
    if not approved_design_path.is_file():
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_workspace_authority:{approved_design_path}")
    actual_design_sha = compute_file_sha256(approved_design_path)
    if actual_design_sha != approved_design_sha:
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:workspace_authority_mismatch:{approved_design_path}")

    # Verify approved expansion plan file on disk
    if approved_plan_path.is_symlink():
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:symlink_detected:{approved_plan_path}")
    if not approved_plan_path.is_file():
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_workspace_authority:{approved_plan_path}")
    actual_plan_sha = compute_file_sha256(approved_plan_path)
    if actual_plan_sha != approved_plan_sha:
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:workspace_authority_mismatch:{approved_plan_path}")

    # Verify network authorization file on disk
    if network_authorization_path.is_symlink():
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:symlink_detected:{network_authorization_path}")
    if not network_authorization_path.is_file():
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_workspace_authority:{network_authorization_path}")
    actual_net_auth_sha = compute_file_sha256(network_authorization_path)
    if actual_net_auth_sha != network_authorization_sha:
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:workspace_authority_mismatch:{network_authorization_path}")

    try:
        auth_json = json.loads(network_authorization_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:invalid_auth_json:{exc}") from exc

    required_auth_keys = {"run_id", "approved_design_sha256", "approved_plan_sha256"}
    if not isinstance(auth_json, dict) or set(auth_json.keys()) != required_auth_keys:
        raise CandidateEvidenceSourceError("candidate_root_invalid:network_auth_keys_mismatch")
    if auth_json["run_id"] != manifest["run_id"]:
        raise CandidateEvidenceSourceError("candidate_root_invalid:network_auth_run_id_mismatch")
    if auth_json["approved_design_sha256"] != approved_design_sha:
        raise CandidateEvidenceSourceError("candidate_root_invalid:network_auth_design_sha_mismatch")
    if auth_json["approved_plan_sha256"] != approved_plan_sha:
        raise CandidateEvidenceSourceError("candidate_root_invalid:network_auth_plan_sha_mismatch")

    for rel_p, key in FIXED_AUTHORITY_KEY_MAP.items():
        exp_sha = EXACT_AUTHORITY_FILES[key]
        if auth_pkt[key]["sha256"] != exp_sha:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:authority_packet_sha_mismatch:{key}")
        disk_p = root_dir / rel_p
        if disk_p.is_symlink():
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:symlink_detected:{rel_p}")
        if not disk_p.is_file():
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_workspace_authority:{rel_p}")
        actual_sha = compute_file_sha256(disk_p)
        if actual_sha != exp_sha:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:workspace_authority_mismatch:{rel_p}")

    # Re-verify cohort from canonical C input
    c_comp_path = root_dir / "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z/completion_manifest.json"
    matrix_p = root_dir / "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json"
    if not c_comp_path.is_file():
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_workspace_authority:{c_comp_path}")
    if not matrix_p.is_file():
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_workspace_authority:{matrix_p}")

    c_completed = c_comp_path.parent
    b_export = root_dir / "data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090"
    if not b_export.is_dir():
        raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_workspace_authority:{b_export}")
    verified_c = verify_c_input(project_root=root_dir, completed_root=c_completed, source_export=b_export)
    expected_cohort = derive_candidate_cohort(verified_c, matrix_p)
    if manifest["cohort"] != expected_cohort:
        raise CandidateEvidenceSourceError("candidate_root_invalid:cohort_mismatch")
    if len(manifest["cohort"]) != 41:
        raise CandidateEvidenceSourceError("candidate_root_invalid:cohort_length_not_41")

    # Re-verify logical records and physical objects against frozen matrix
    _, exp_logical, exp_physical = enumerate_candidate_requests(
        coverage_matrix_path=matrix_p,
        cohort=manifest["cohort"],
    )
    if len(manifest["logical_archive_records"]) != len(exp_logical):
        raise CandidateEvidenceSourceError(
            f"candidate_root_invalid:logical_records_count_mismatch:{len(manifest['logical_archive_records'])}!={len(exp_logical)}"
        )
    if len(manifest["physical_source_objects"]) != len(exp_physical):
        raise CandidateEvidenceSourceError(
            f"candidate_root_invalid:physical_objects_count_mismatch:{len(manifest['physical_source_objects'])}!={len(exp_physical)}"
        )

    exp_log_map = {r["logical_archive_record_id"]: r for r in exp_logical}
    for log_rec in manifest["logical_archive_records"]:
        l_keys = set(log_rec.keys())
        if l_keys != EXPECTED_LOGICAL_RECORD_KEYS:
            missing = EXPECTED_LOGICAL_RECORD_KEYS - l_keys
            extra = l_keys - EXPECTED_LOGICAL_RECORD_KEYS
            raise CandidateEvidenceSourceError(
                f"candidate_root_invalid:logical_record_keys_mismatch:missing={missing},extra={extra}"
            )
        lid = log_rec["logical_archive_record_id"]
        if lid not in exp_log_map:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:unexpected_logical_record_id:{lid}")
        exp_rec = exp_log_map[lid]
        if log_rec["matrix_record_sha256"] != exp_rec["matrix_record_sha256"]:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:matrix_record_sha_mismatch:{lid}")
        if log_rec["matrix_record_projection_v1"] != exp_rec["matrix_record_projection_v1"]:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:matrix_record_projection_mismatch:{lid}")
        if log_rec["physical_source_object_id"] != exp_rec["physical_source_object_id"]:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:logical_physical_id_mismatch:{lid}")
        if log_rec["exact_source_url"] != exp_rec["exact_source_url"]:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:logical_exact_source_url_mismatch:{lid}")
        if log_rec["coverage_matrix_sha256"] != exp_rec["coverage_matrix_sha256"]:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:logical_matrix_sha_mismatch:{lid}")

    exp_phys_map = {p["physical_source_object_id"]: p for p in exp_physical}
    for p in manifest["physical_source_objects"]:
        p_keys = set(p.keys())
        if p_keys != EXPECTED_PHYSICAL_OBJECT_KEYS:
            missing = EXPECTED_PHYSICAL_OBJECT_KEYS - p_keys
            extra = p_keys - EXPECTED_PHYSICAL_OBJECT_KEYS
            raise CandidateEvidenceSourceError(
                f"candidate_root_invalid:physical_object_keys_mismatch:missing={missing},extra={extra}"
            )
        pid = p["physical_source_object_id"]
        if pid not in exp_phys_map:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:unexpected_physical_source_object_id:{pid}")
        exp_p = exp_phys_map[pid]
        if p["exact_source_url"] != exp_p["exact_source_url"]:
            raise CandidateEvidenceSourceError(
                f"candidate_root_invalid:exact_source_url_mismatch:{pid}:{p['exact_source_url']}!={exp_p['exact_source_url']}"
            )
        derived_pid = compute_physical_source_object_id(p["exact_source_url"])
        if derived_pid != pid:
            raise CandidateEvidenceSourceError(
                f"candidate_root_invalid:physical_id_url_hash_mismatch:{pid}!={derived_pid}"
            )

    for cov_entry in manifest["metric_window_coverages"]:
        c_keys = set(cov_entry.keys())
        if c_keys != EXPECTED_METRIC_WINDOW_COVERAGE_KEYS:
            missing = EXPECTED_METRIC_WINDOW_COVERAGE_KEYS - c_keys
            extra = c_keys - EXPECTED_METRIC_WINDOW_COVERAGE_KEYS
            raise CandidateEvidenceSourceError(
                f"candidate_root_invalid:metric_window_coverage_keys_mismatch:missing={missing},extra={extra}"
            )

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
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:illegal_physical_fetch_status:{st}")
        phys_status_map[p["physical_source_object_id"]] = st

    for log_rec in manifest["logical_archive_records"]:
        st = log_rec.get("record_state")
        if st not in allowed_terminal_statuses:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:illegal_logical_record_state:{st}")
        pid = log_rec["physical_source_object_id"]
        if st != phys_status_map.get(pid):
            raise CandidateEvidenceSourceError(
                f"candidate_root_invalid:record_state_mismatch_with_physical:{st}!={phys_status_map.get(pid)}"
            )

    declared_files = {"candidate_manifest.json"}
    for p in manifest["physical_source_objects"]:
        if p["zip_relative_path"] is not None:
            declared_files.add(p["zip_relative_path"])
        if p["csv_relative_path"] is not None:
            declared_files.add(p["csv_relative_path"])

    for item in completed_root.rglob("*"):
        if item.is_symlink():
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:symlink_detected:{item}")
        if item.is_file():
            rel = str(item.relative_to(completed_root))
            if rel.endswith(".tmp") or ".tmp." in rel:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:stale_temp_file:{rel}")
            if rel not in declared_files:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:unexpected_file:{rel}")
        elif item.is_dir():
            rel = str(item.relative_to(completed_root))
            if rel not in ("zips", "csvs"):
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:unexpected_dir:{rel}")

    seen_phys_ids = set()
    seen_zip_paths = set()
    seen_csv_paths = set()
    for p in manifest["physical_source_objects"]:
        pid = p["physical_source_object_id"]
        if pid in seen_phys_ids:
            raise CandidateEvidenceSourceError(f"candidate_root_invalid:duplicate_physical_id:{pid}")
        seen_phys_ids.add(pid)

        z_rel = p["zip_relative_path"]
        if z_rel is not None:
            if z_rel in seen_zip_paths:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:duplicate_zip_path:{z_rel}")
            seen_zip_paths.add(z_rel)
            z_path = completed_root / z_rel
            if not z_path.is_file():
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_zip_file:{z_rel}")
            if z_path.stat().st_size != p["zip_byte_length"]:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:zip_length_mismatch:{z_rel}")
            if compute_file_sha256(z_path) != p["zip_sha256"]:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:zip_sha_mismatch:{z_rel}")

        c_rel = p["csv_relative_path"]
        if c_rel is not None:
            if c_rel in seen_csv_paths:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:duplicate_csv_path:{c_rel}")
            seen_csv_paths.add(c_rel)
            c_path = completed_root / c_rel
            if not c_path.is_file():
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_csv_file:{c_rel}")
            if c_path.stat().st_size != p["csv_byte_length"]:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:csv_length_mismatch:{c_rel}")
            if compute_file_sha256(c_path) != p["csv_sha256"]:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:csv_sha_mismatch:{c_rel}")

    # Re-read and re-parse CSV files from disk
    recomputed_in_memory_rows: Dict[str, List[Dict[str, Any]]] = {}
    for p in manifest["physical_source_objects"]:
        pid = p["physical_source_object_id"]
        c_rel = p["csv_relative_path"]
        if p["fetch_status"] == "fetched_verified":
            if c_rel is None:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_csv_path_for_verified_object:{pid}")
            c_path = completed_root / c_rel
            if not c_path.is_file():
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:missing_csv_file:{c_rel}")

            ref_logical = [r for r in manifest["logical_archive_records"] if r["physical_source_object_id"] == pid]
            if not ref_logical:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:unreferenced_physical_id:{pid}")
            family = ref_logical[0]["metric"]
            symbol = ref_logical[0]["canonical_symbol"]

            c_status, c_reason, raw_header, row_cnt, first_r, last_r, parsed_rows = parse_and_validate_csv(
                family=family,
                csv_source=c_path,
                expected_symbol=symbol,
            )
            if c_status != "fetched_verified":
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:csv_revalidation_failed:{pid}:{c_reason}")
            if row_cnt != p["csv_row_count"]:
                raise CandidateEvidenceSourceError(
                    f"candidate_root_invalid:row_count_mismatch:{pid}:{row_cnt}!={p['csv_row_count']}"
                )
            if first_r != p["first_row"]:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:first_row_mismatch:{pid}")
            if last_r != p["last_row"]:
                raise CandidateEvidenceSourceError(f"candidate_root_invalid:last_row_mismatch:{pid}")
            recomputed_in_memory_rows[pid] = parsed_rows
        else:
            recomputed_in_memory_rows[pid] = []

    # Recompute coverages independently
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

    parsed_series: Dict[Tuple[str, str, str, str], List[Dict[str, Any]]] = {}

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
            # Store parsed series keyed by (parent_article_id, contract_id, canonical_symbol, metric)
            series_key = (grp_key[0], grp_key[1], grp_key[2], grp_key[4])
            if series_key not in parsed_series:
                parsed_series[series_key] = []
            # Attach metadata to rows for lineage tracing
            for j_row in joined_rows:
                row_copy = dict(j_row)
                row_copy["_window"] = first_rec["window"]
                row_copy["_logical_archive_record_id"] = first_rec["logical_archive_record_id"]
                row_copy["_physical_source_object_id"] = first_rec["physical_source_object_id"]
                parsed_series[series_key].append(row_copy)
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
        raise CandidateEvidenceSourceError(
            f"candidate_root_invalid:coverages_count_mismatch:{len(recomputed_coverages)}!={len(manifest['metric_window_coverages'])}"
        )
    for idx, (exp_c, act_c) in enumerate(zip(recomputed_coverages, manifest["metric_window_coverages"])):
        if exp_c != act_c:
            raise CandidateEvidenceSourceError(
                f"candidate_root_invalid:coverage_entry_mismatch:index_{idx}"
            )

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
        raise CandidateEvidenceSourceError(
            f"candidate_root_invalid:root_state_mismatch:{manifest['candidate_root_state']}!={expected_state}"
        )

    return VerifiedCandidateEvidence(
        run_id=manifest["run_id"],
        completed_root=completed_root,
        manifest=manifest,
        cohort=manifest["cohort"],
        physical_source_objects=manifest["physical_source_objects"],
        logical_archive_records=manifest["logical_archive_records"],
        metric_window_coverages=manifest["metric_window_coverages"],
        candidate_root_state=manifest["candidate_root_state"],
        authority_packet=manifest["authority_packet"],
        authority_flags=manifest["authority_flags"],
        parsed_series=parsed_series,
    )


def load_verified_candidate_evidence(
    *,
    project_root: Path,
    candidate_root: Path,
    approved_design_path: Path,
    approved_design_sha: str,
    approved_plan_path: Path,
    approved_plan_sha: str,
    network_authorization_path: Path,
    network_authorization_sha: str,
) -> VerifiedCandidateEvidence:
    """Exact-002 admission wrapper admitting only canonical candidate root and manifest."""
    root_dir = project_root.resolve()
    resolved_candidate = candidate_root.resolve()
    expected_root = (root_dir / CANONICAL_CANDIDATE_RELATIVE_PATH).resolve()

    if resolved_candidate != expected_root:
        raise CandidateEvidenceSourceError(
            f"candidate_admission_invalid:candidate_root_path_mismatch:{resolved_candidate}!={expected_root}"
        )

    if candidate_root.name != CANONICAL_CANDIDATE_RUN_ID:
        raise CandidateEvidenceSourceError(
            f"candidate_admission_invalid:run_id_mismatch:{candidate_root.name}!={CANONICAL_CANDIDATE_RUN_ID}"
        )

    manifest_p = candidate_root / "candidate_manifest.json"
    if not manifest_p.is_file():
        raise CandidateEvidenceSourceError("candidate_admission_invalid:missing_manifest")
    if manifest_p.is_symlink():
        raise CandidateEvidenceSourceError("candidate_admission_invalid:symlink_manifest")

    actual_manifest_sha = compute_file_sha256(manifest_p)
    if actual_manifest_sha != CANONICAL_CANDIDATE_MANIFEST_SHA256:
        raise CandidateEvidenceSourceError(
            f"candidate_admission_invalid:manifest_sha_mismatch:{actual_manifest_sha}!={CANONICAL_CANDIDATE_MANIFEST_SHA256}"
        )

    # Enforce canonical network authorization path under project root
    expected_net_auth_path = (root_dir / FROZEN_NETWORK_AUTH_RELATIVE_PATH).resolve()
    resolved_net_auth_path = network_authorization_path.resolve()
    if resolved_net_auth_path != expected_net_auth_path:
        raise CandidateEvidenceSourceError(
            f"candidate_admission_invalid:network_auth_path_not_canonical:{resolved_net_auth_path}!={expected_net_auth_path}"
        )
    if network_authorization_path.is_symlink():
        raise CandidateEvidenceSourceError(f"candidate_admission_invalid:symlink_detected:{network_authorization_path}")
    if not network_authorization_path.is_file():
        raise CandidateEvidenceSourceError(
            f"candidate_admission_invalid:missing_network_authorization:{network_authorization_path}"
        )
    actual_net_auth_sha = compute_file_sha256(network_authorization_path)
    if actual_net_auth_sha != network_authorization_sha:
        raise CandidateEvidenceSourceError(
            f"candidate_admission_invalid:network_auth_sha_mismatch:{actual_net_auth_sha}!={network_authorization_sha}"
        )

    return validate_candidate_root_core(
        completed_root=candidate_root,
        approved_design_path=approved_design_path,
        approved_design_sha=approved_design_sha,
        approved_plan_path=approved_plan_path,
        approved_plan_sha=approved_plan_sha,
        network_authorization_path=network_authorization_path,
        network_authorization_sha=network_authorization_sha,
        project_root=project_root,
    )


def bind_verified_candidate_c_authority(
    *,
    verified_candidate: VerifiedCandidateEvidence,
    verified_c: VerifiedCInput,
    completed_root: Path,
    source_export: Path,
) -> None:
    """Cross-bind verified C, receipt and B sealed-export byte authorities."""
    c_manifest_path = completed_root / "completion_manifest.json"
    if not c_manifest_path.is_file():
        raise CandidateEvidenceSourceError(f"STOP=upstream_denominator_authority_invalid:missing_c_manifest:{c_manifest_path}")
    c_manifest_sha = compute_file_sha256(c_manifest_path)

    b_manifest_path = source_export / "sealed_export_manifest.json"
    if not b_manifest_path.is_file():
        raise CandidateEvidenceSourceError(f"STOP=upstream_denominator_authority_invalid:missing_b_manifest:{b_manifest_path}")
    b_manifest_sha = compute_file_sha256(b_manifest_path)

    auth_pkt = verified_candidate.authority_packet
    exp_c_sha = auth_pkt["c_completion_manifest"]["sha256"]
    exp_receipt_sha = auth_pkt["c_source_export_receipt"]["sha256"]
    exp_b_sha = auth_pkt["b_sealed_export_manifest"]["sha256"]

    if c_manifest_sha != exp_c_sha:
        raise CandidateEvidenceSourceError(
            f"STOP=upstream_denominator_authority_invalid:c_completion_manifest_sha_mismatch:{c_manifest_sha}!={exp_c_sha}"
        )
    if verified_c.source_export_receipt_sha256 != exp_receipt_sha:
        raise CandidateEvidenceSourceError(
            f"STOP=upstream_denominator_authority_invalid:source_export_receipt_sha_mismatch:{verified_c.source_export_receipt_sha256}!={exp_receipt_sha}"
        )
    if b_manifest_sha != exp_b_sha:
        raise CandidateEvidenceSourceError(
            f"STOP=upstream_denominator_authority_invalid:b_sealed_export_manifest_sha_mismatch:{b_manifest_sha}!={exp_b_sha}"
        )
    if verified_c.input_manifest_sha256 != exp_b_sha:
        raise CandidateEvidenceSourceError(
            f"STOP=upstream_denominator_authority_invalid:c_input_manifest_sha_mismatch:{verified_c.input_manifest_sha256}!={exp_b_sha}"
        )


def bind_candidate_publication_authority(
    *,
    verified_candidate: VerifiedCandidateEvidence,
    verified_c: VerifiedCInput,
) -> Mapping[CandidateIdentity, PublicationAuthority]:
    """Derive canonical publication authority for all candidate events."""
    outcomes = parse_parent_audit_outcomes(verified_c)
    notices = parse_delisting_notices(verified_c)

    outcomes_map = {
        (o.get("source_article_id") or o.get("parent_article_id")): o
        for o in outcomes
        if (o.get("source_article_id") or o.get("parent_article_id"))
    }
    notices_map = {
        (n.get("source_article_id") or n.get("parent_article_id")): n
        for n in notices
        if (n.get("source_article_id") or n.get("parent_article_id"))
    }

    # Group candidate records by identity to verify W1 windows
    coverage_w1_by_id: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for cov in verified_candidate.metric_window_coverages:
        if cov["window"] == "w1_shock_12h":
            id_key = (cov["parent_article_id"], cov["contract_id"], cov["canonical_symbol"])
            if id_key not in coverage_w1_by_id:
                coverage_w1_by_id[id_key] = []
            coverage_w1_by_id[id_key].append(cov)

    authorities: Dict[CandidateIdentity, PublicationAuthority] = {}

    for id_key, cov_list in coverage_w1_by_id.items():
        parent_id, contract_id, symbol = id_key
        outcome = outcomes_map.get(parent_id)
        notice = notices_map.get(parent_id)

        if outcome is None or notice is None:
            raise CandidateEvidenceSourceError(
                f"STOP=upstream_denominator_authority_invalid:missing_parent_record:{parent_id}"
            )

        t_pub_outcome = outcome.get("source_published_at_ms")
        if not isinstance(t_pub_outcome, int) or isinstance(t_pub_outcome, bool):
            raise CandidateEvidenceSourceError(
                f"STOP=upstream_denominator_authority_invalid:outcome_tpub_not_int:{parent_id}:{t_pub_outcome}"
            )
        if not (1_000_000_000_000 <= t_pub_outcome < 10_000_000_000_000):
            raise CandidateEvidenceSourceError(
                f"STOP=upstream_denominator_authority_invalid:outcome_tpub_out_of_range:{parent_id}:{t_pub_outcome}"
            )
        if outcome.get("publication_time_status") != "present":
            raise CandidateEvidenceSourceError(
                f"STOP=upstream_denominator_authority_invalid:publication_time_status_not_present:{parent_id}"
            )

        t_pub_notice = notice.get("source_published_at_ms")
        if t_pub_notice != t_pub_outcome:
            raise CandidateEvidenceSourceError(
                f"STOP=upstream_denominator_authority_invalid:notice_outcome_tpub_mismatch:{parent_id}:{t_pub_notice}!={t_pub_outcome}"
            )

        # Check candidate W1 coverages match Tpub and Tpub + 12h
        for cov in cov_list:
            if cov["requested_interval_start_ms"] != t_pub_outcome:
                raise CandidateEvidenceSourceError(
                    f"STOP=upstream_denominator_authority_invalid:w1_start_mismatch:{id_key}:{cov['requested_interval_start_ms']}!={t_pub_outcome}"
                )
            if cov["requested_interval_end_ms"] != t_pub_outcome + 12 * 3600 * 1000:
                raise CandidateEvidenceSourceError(
                    f"STOP=upstream_denominator_authority_invalid:w1_end_mismatch:{id_key}:{cov['requested_interval_end_ms']}!={t_pub_outcome + 12 * 3600 * 1000}"
                )

        ident = CandidateIdentity(
            parent_article_id=parent_id,
            contract_id=contract_id,
            canonical_symbol=symbol,
        )
        authorities[ident] = PublicationAuthority(
            parent_article_id=parent_id,
            contract_id=contract_id,
            canonical_symbol=symbol,
            t_pub_ms=t_pub_outcome,
            publication_time_authority="parent_audit_outcomes.source_published_at_ms_selected_trusted_bapi_publishDate",
        )

    return authorities
