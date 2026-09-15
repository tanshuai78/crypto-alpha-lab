"""Source verification and retained-byte transaction for Stage 1.6F historical diagnostic."""

import hashlib
import io
import json
import math
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter_storage import (
    load_completed_adapter_audit,
)


class Stage16FDiagnosticError(Exception):
    """Base exception for Stage 1.6F historical mechanism diagnostic."""
    pass


class SourceInvalidError(Stage16FDiagnosticError):
    """Raised when upstream C completed root fails validation."""
    pass


class MarketEvidenceInvalidError(Stage16FDiagnosticError):
    """Raised when offline market evidence package fails validation."""
    pass


REQUIRED_C_AUTHORITATIVE_ARTIFACTS: Tuple[str, ...] = (
    "source_export_receipt.json",
    "audit_candidate_manifest.json",
    "parent_audit_outcomes.jsonl",
    "detail_revisions.jsonl",
    "semantic_extractions.jsonl",
    "delisting_notices.jsonl",
    "delisting_contracts.jsonl",
    "audit_diagnostics.jsonl",
    "stage1_6a_futures_delisting_source_audit_summary.json",
)


@dataclass(frozen=True)
class VerifiedCInput:
    """Immutable verified C retained-byte input and identity."""
    input_export_id: str
    input_manifest_sha256: str
    source_export_receipt_sha256: str
    authoritative_artifacts: Tuple[Dict[str, Any], ...]
    retained_bytes: Dict[str, bytes]
    retained_sha256: Dict[str, str]
    completion_manifest: Dict[str, Any]
    summary: Dict[str, Any]
    receipt: Dict[str, Any]


def verify_c_input(
    project_root: Path,
    completed_root: Path,
    source_export: Path,
) -> VerifiedCInput:
    """
    Executes the Parent Design Section 4.1 C -> F retained-byte transaction.
    1. Calls load_completed_adapter_audit exactly once.
    2. Validates completion_manifest: status=complete, source_audit_passed is True.
    3. Validates exact required nine authoritative artifacts without duplicate or extras.
    4. Reads each artifact exactly once from disk, checks byte length and SHA-256 against manifest.
    5. Validates that retained JSON/JSONL can be parsed.
    6. Returns an immutable VerifiedCInput containing retained bytes; downstream F never reopens C paths.
    """
    try:
        loaded = load_completed_adapter_audit(
            project_root=project_root,
            output_root=completed_root,
            source_export=source_export,
        )
    except Exception as exc:
        raise SourceInvalidError(f"source_invalid: c_loader_failed: {exc}") from exc

    if not isinstance(loaded, dict):
        raise SourceInvalidError("source_invalid: loader_returned_invalid_structure")

    completion_manifest = loaded["completion_manifest"]
    summary = loaded["summary"]
    receipt = loaded["receipt"]

    if not isinstance(completion_manifest, dict):
        raise SourceInvalidError("source_invalid: completion_manifest_missing")
    if completion_manifest["status"] != "complete":
        raise SourceInvalidError("source_invalid: completion_status_not_complete")
    if completion_manifest["source_audit_passed"] is not True:
        raise SourceInvalidError("source_invalid: source_audit_passed_not_true")

    artifacts = completion_manifest["authoritative_artifacts"]
    if not isinstance(artifacts, list):
        raise SourceInvalidError("source_invalid: authoritative_artifacts_not_list")

    seen_paths = set()
    for art in artifacts:
        if not isinstance(art, dict):
            raise SourceInvalidError("source_invalid: artifact_entry_not_dict")
        rel_p = art["relative_path"]
        if not isinstance(rel_p, str):
            raise SourceInvalidError("source_invalid: artifact_relative_path_missing")
        if ".." in rel_p or rel_p.startswith("/"):
            raise SourceInvalidError(f"source_invalid: artifact_path_traversal: {rel_p}")
        if rel_p in seen_paths:
            raise SourceInvalidError(f"source_invalid: duplicate_authoritative_artifact: {rel_p}")
        seen_paths.add(rel_p)

    required_set = set(REQUIRED_C_AUTHORITATIVE_ARTIFACTS)
    if seen_paths != required_set:
        missing = required_set - seen_paths
        extra = seen_paths - required_set
        raise SourceInvalidError(
            f"source_invalid: authoritative_artifacts_mismatch (missing: {missing}, extra: {extra})"
        )

    resolved_completed_root = completed_root.resolve(strict=True)
    retained_bytes: Dict[str, bytes] = {}
    retained_sha256: Dict[str, str] = {}

    for art in artifacts:
        rel_p = art["relative_path"]
        expected_sha = art["sha256"]
        expected_length = art["byte_length"]

        if not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise SourceInvalidError(f"source_invalid: invalid_expected_sha: {rel_p}")
        if not isinstance(expected_length, int) or expected_length < 0:
            raise SourceInvalidError(f"source_invalid: invalid_expected_length: {rel_p}")

        file_p = resolved_completed_root / rel_p
        if not file_p.is_file() or file_p.is_symlink():
            raise SourceInvalidError(f"source_invalid: artifact_not_regular_file: {rel_p}")

        try:
            content = file_p.read_bytes()
        except Exception as exc:
            raise SourceInvalidError(f"source_invalid: artifact_read_failed: {rel_p}: {exc}") from exc

        if len(content) != expected_length:
            raise SourceInvalidError(
                f"source_invalid: byte_length_mismatch for {rel_p}: expected {expected_length}, got {len(content)}"
            )

        actual_sha = hashlib.sha256(content).hexdigest()
        if actual_sha != expected_sha:
            raise SourceInvalidError(
                f"source_invalid: sha256_mismatch for {rel_p}: expected {expected_sha}, got {actual_sha}"
            )

        # Pre-validate JSON/JSONL structure
        try:
            decoded = content.decode("utf-8")
            if rel_p.endswith(".json"):
                json.loads(decoded)
            elif rel_p.endswith(".jsonl"):
                for line in decoded.splitlines():
                    line_str = line.strip()
                    if line_str:
                        json.loads(line_str)
        except Exception as exc:
            raise SourceInvalidError(f"source_invalid: malformed_retained_json: {rel_p}: {exc}") from exc

        retained_bytes[rel_p] = content
        retained_sha256[rel_p] = actual_sha

    input_export_id = completion_manifest["input_export_id"]
    input_manifest_sha256 = completion_manifest["input_manifest_sha256"]
    source_export_receipt_sha256 = completion_manifest["source_export_receipt_sha256"]

    if not isinstance(input_export_id, str) or not input_export_id:
        raise SourceInvalidError("source_invalid: input_export_id_missing")
    if not isinstance(input_manifest_sha256, str) or not input_manifest_sha256:
        raise SourceInvalidError("source_invalid: input_manifest_sha256_missing")
    if not isinstance(source_export_receipt_sha256, str) or not source_export_receipt_sha256:
        raise SourceInvalidError("source_invalid: source_export_receipt_sha256_missing")

    return VerifiedCInput(
        input_export_id=input_export_id,
        input_manifest_sha256=input_manifest_sha256,
        source_export_receipt_sha256=source_export_receipt_sha256,
        authoritative_artifacts=tuple(artifacts),
        retained_bytes=retained_bytes,
        retained_sha256=retained_sha256,
        completion_manifest=completion_manifest,
        summary=summary,
        receipt=receipt,
    )


def parse_receipt(verified_c: VerifiedCInput) -> Dict[str, Any]:
    return json.loads(verified_c.retained_bytes["source_export_receipt.json"].decode("utf-8"))


def parse_summary(verified_c: VerifiedCInput) -> Dict[str, Any]:
    return json.loads(
        verified_c.retained_bytes["stage1_6a_futures_delisting_source_audit_summary.json"].decode("utf-8")
    )


def parse_candidate_manifest(verified_c: VerifiedCInput) -> Dict[str, Any]:
    return json.loads(verified_c.retained_bytes["audit_candidate_manifest.json"].decode("utf-8"))


def _parse_jsonl(raw_bytes: bytes) -> List[Dict[str, Any]]:
    return [
        json.loads(line)
        for line in raw_bytes.decode("utf-8").splitlines()
        if line.strip()
    ]


def parse_parent_audit_outcomes(verified_c: VerifiedCInput) -> List[Dict[str, Any]]:
    return _parse_jsonl(verified_c.retained_bytes["parent_audit_outcomes.jsonl"])


def parse_detail_revisions(verified_c: VerifiedCInput) -> List[Dict[str, Any]]:
    return _parse_jsonl(verified_c.retained_bytes["detail_revisions.jsonl"])


def parse_semantic_extractions(verified_c: VerifiedCInput) -> List[Dict[str, Any]]:
    return _parse_jsonl(verified_c.retained_bytes["semantic_extractions.jsonl"])


def parse_delisting_notices(verified_c: VerifiedCInput) -> List[Dict[str, Any]]:
    return _parse_jsonl(verified_c.retained_bytes["delisting_notices.jsonl"])


def parse_delisting_contracts(verified_c: VerifiedCInput) -> List[Dict[str, Any]]:
    return _parse_jsonl(verified_c.retained_bytes["delisting_contracts.jsonl"])


def parse_audit_diagnostics(verified_c: VerifiedCInput) -> List[Dict[str, Any]]:
    return _parse_jsonl(verified_c.retained_bytes["audit_diagnostics.jsonl"])


# ---------------------------------------------------------------------------
# Stage 1.6F Task 2: Offline Market-Evidence Verification And Strict Parsers
# ---------------------------------------------------------------------------

REVIEWED_MARKET_EVIDENCE_MANIFEST_SHA256 = (
    "9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f"
)
REVIEWED_MARKET_EVIDENCE_MANIFEST_SCHEMA_VERSION = (
    "stage1_6f_gap02_evidence_manifest_v1"
)

AUXILIARY_ARTIFACT_SPECS: Dict[str, Dict[str, Any]] = {
    "historical_universe_snapshot_20250115.json": {
        "sha256": "63449f932636893a0b24466d04e79b2456553ad8d9502f677f8d6b66d197d5e8",
        "byte_length": 258001,
    },
    "historical_control_candidates_baseline_provenance_reef_20250115.json": {
        "sha256": "e34da67918daa8be84a7dbc647918decc40bdd6a9fd4bf8a521ae9ce1f2b68ad",
        "byte_length": 1256816,
    },
    "historical_control_universe_reef_20250115.json": {
        "sha256": "b3042945036fe4825b7fc1e40150be438805a706b8dd1e5b80ac849a3808cdb0",
        "byte_length": 159983,
    },
    "denominator_archive_coverage_matrix_all_intersecting.json": {
        "sha256": "b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8",
        "byte_length": 1488347,
    },
    "settlement_rule_mapping_37contracts.json": {
        "sha256": "40b338651644d9d141f075f1dc78b8f219b435d52a8e9246eebbe33b3b4b7601",
        "byte_length": 49226,
    },
    "data_semantics_contract.json": {
        "sha256": "5a096c50b194521ccc1402884ee15364783b1201a2c5fb0d289d64548cd38fd2",
        "byte_length": 4713,
    },
}

OFFICIAL_SOURCES_SPECS: Dict[str, Dict[str, Any]] = {
    "official_sources/s3_binance_vision_futures_um_klines_symbols_list.xml": {
        "sha256": "885835e03ebeb93d92b957804fafe55565606ddc9492930519aed91941e03072",
        "byte_length": 91956,
    },
    "official_sources/binance_announcement_settlement_4bcabddf0e81423ebca242e185bf157d.html": {
        "sha256": "2ba30d566e99928c4df332dbda6a62aaf1a4e9d39a0048f3c40d0266e5b6dd36",
        "byte_length": 56179,
    },
    "official_sources/binance_faq_funding_rate_360033525031.html": {
        "sha256": "9266dac6d2dd6c3bd873a0fd4da7bc0780026fe79dcfb241c2e0f0db9cd953ca",
        "byte_length": 67159,
    },
    "official_sources/binance_faq_mark_price_360033525011.html": {
        "sha256": "3604bf98774f37a7b67078c7c8b28454ad5e9bc1f9f3b1eac9f71d24c139a64a",
        "byte_length": 50101,
    },
}

EXACT_CSV_HEADERS: Dict[str, str] = {
    "klines_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "klines_1m": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "mark_price_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "index_price_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "premium_index_1h": "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore",
    "metrics_5m": "create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio",
    "funding_rate": "calc_time,funding_interval_hours,last_funding_rate",
    "book_depth": "timestamp,percentage,depth,notional",
    "agg_trades": "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
}


def _check_finite_float(raw_val: str, field_name: str) -> float:
    try:
        val = float(raw_val)
    except (ValueError, TypeError) as exc:
        raise MarketEvidenceInvalidError(
            f"market_evidence_invalid: invalid_float for {field_name}: {raw_val}"
        ) from exc
    if not math.isfinite(val) or math.isnan(val):
        raise MarketEvidenceInvalidError(
            f"market_evidence_invalid: non_finite_float for {field_name}: {raw_val}"
        )
    return val


def _check_optional_finite_float(raw_val: str, field_name: str) -> Optional[float]:
    raw_val_str = raw_val.strip()
    if not raw_val_str:
        return None
    return _check_finite_float(raw_val_str, field_name)


def _check_int(raw_val: str, field_name: str) -> int:
    try:
        return int(raw_val)
    except (ValueError, TypeError) as exc:
        raise MarketEvidenceInvalidError(
            f"market_evidence_invalid: invalid_int for {field_name}: {raw_val}"
        ) from exc


def _parse_timestamp_ms(raw_val: str, field_name: str) -> int:
    try:
        if raw_val.isdigit() or (raw_val.startswith("-") and raw_val[1:].isdigit()):
            return int(raw_val)
        dt = datetime.strptime(raw_val, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception as exc:
        raise MarketEvidenceInvalidError(
            f"market_evidence_invalid: invalid_timestamp for {field_name}: {raw_val}"
        ) from exc


def resolve_csv_family(rel_category: str) -> str:
    if rel_category in (
        "klines_1h", "klines_1m", "mark_price_1h", "index_price_1h", "premium_index_1h",
        "metrics_5m", "funding_rate", "book_depth", "agg_trades"
    ):
        return rel_category
    if "kline" in rel_category or "control_candidate" in rel_category:
        return "klines_1h"
    raise MarketEvidenceInvalidError(f"market_evidence_invalid: unknown_category: {rel_category}")


def parse_strict_csv(data_bytes: bytes, rel_category: str) -> List[Dict[str, Any]]:
    """Strictly parses CSV bytes according to Delta Section 4.2 frozen headers and finite values."""
    try:
        text = data_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MarketEvidenceInvalidError(f"market_evidence_invalid: invalid_utf8: {exc}") from exc

    family = resolve_csv_family(rel_category)
    expected_header = EXACT_CSV_HEADERS[family]

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise MarketEvidenceInvalidError("market_evidence_invalid: empty_csv")

    header_line = lines[0]
    if header_line != expected_header:
        raise MarketEvidenceInvalidError(
            f"market_evidence_invalid: header_mismatch for {rel_category}: expected {expected_header}, got {header_line}"
        )

    rows: List[Dict[str, Any]] = []
    for line in lines[1:]:
        parts = line.split(",")
        if family in ("klines_1h", "klines_1m", "mark_price_1h", "index_price_1h", "premium_index_1h"):
            if len(parts) != 12:
                raise MarketEvidenceInvalidError(f"market_evidence_invalid: invalid_column_count: {len(parts)}")
            rows.append({
                "open_time": _check_int(parts[0], "open_time"),
                "open": _check_finite_float(parts[1], "open"),
                "high": _check_finite_float(parts[2], "high"),
                "low": _check_finite_float(parts[3], "low"),
                "close": _check_finite_float(parts[4], "close"),
                "volume": _check_finite_float(parts[5], "volume"),
                "close_time": _check_int(parts[6], "close_time"),
                "quote_volume": _check_finite_float(parts[7], "quote_volume"),
                "count": _check_int(parts[8], "count"),
                "taker_buy_volume": _check_finite_float(parts[9], "taker_buy_volume"),
                "taker_buy_quote_volume": _check_finite_float(parts[10], "taker_buy_quote_volume"),
                "ignore": parts[11],
            })
        elif family == "metrics_5m":
            if len(parts) != 8:
                raise MarketEvidenceInvalidError(f"market_evidence_invalid: invalid_column_count: {len(parts)}")
            rows.append({
                "create_time": _parse_timestamp_ms(parts[0], "create_time"),
                "symbol": parts[1],
                "sum_open_interest": _check_finite_float(parts[2], "sum_open_interest"),
                "sum_open_interest_value": _check_finite_float(parts[3], "sum_open_interest_value"),
                "count_toptrader_long_short_ratio": _check_optional_finite_float(parts[4], "count_toptrader_long_short_ratio"),
                "sum_toptrader_long_short_ratio": _check_optional_finite_float(parts[5], "sum_toptrader_long_short_ratio"),
                "count_long_short_ratio": _check_optional_finite_float(parts[6], "count_long_short_ratio"),
                "sum_taker_long_short_vol_ratio": _check_optional_finite_float(parts[7], "sum_taker_long_short_vol_ratio"),
            })

        elif family == "funding_rate":
            if len(parts) != 3:
                raise MarketEvidenceInvalidError(f"market_evidence_invalid: invalid_column_count: {len(parts)}")
            rows.append({
                "calc_time": _check_int(parts[0], "calc_time"),
                "funding_interval_hours": _check_int(parts[1], "funding_interval_hours"),
                "last_funding_rate": _check_finite_float(parts[2], "last_funding_rate"),
            })
        elif family == "book_depth":
            if len(parts) != 4:
                raise MarketEvidenceInvalidError(f"market_evidence_invalid: invalid_column_count: {len(parts)}")
            rows.append({
                "timestamp": _parse_timestamp_ms(parts[0], "timestamp"),
                "percentage": _check_finite_float(parts[1], "percentage"),
                "depth": _check_finite_float(parts[2], "depth"),
                "notional": _check_finite_float(parts[3], "notional"),
            })

        elif family == "agg_trades":
            if len(parts) != 7:
                raise MarketEvidenceInvalidError(f"market_evidence_invalid: invalid_column_count: {len(parts)}")
            raw_bm = parts[6].strip().lower()
            if raw_bm in ("true", "1"):
                is_buyer_maker = True
            elif raw_bm in ("false", "0"):
                is_buyer_maker = False
            else:
                raise MarketEvidenceInvalidError(
                    f"market_evidence_invalid: invalid_is_buyer_maker: {parts[6]}"
                )
            rows.append({
                "agg_trade_id": _check_int(parts[0], "agg_trade_id"),
                "price": _check_finite_float(parts[1], "price"),
                "quantity": _check_finite_float(parts[2], "quantity"),
                "first_trade_id": _check_int(parts[3], "first_trade_id"),
                "last_trade_id": _check_int(parts[4], "last_trade_id"),
                "transact_time": _check_int(parts[5], "transact_time"),
                "is_buyer_maker": is_buyer_maker,
            })

    return rows


@dataclass(frozen=True)
class VerifiedMarketEvidence:
    """Immutable verified offline market evidence package and series."""
    manifest_sha256: str
    manifest_byte_length: int
    manifest_data: Dict[str, Any]
    auxiliary_artifacts: Dict[str, Any]
    csv_records: Tuple[Dict[str, Any], ...]
    series_by_symbol_and_type: Dict[Tuple[str, str], Tuple[Dict[str, Any], ...]]

    def get_series(self, series_type: str, symbol: str) -> Optional[Tuple[Dict[str, Any], ...]]:
        key = (series_type, symbol)
        if key in self.series_by_symbol_and_type:
            return self.series_by_symbol_and_type[key]
        return None


def verify_market_evidence(market_evidence_root: Path) -> VerifiedMarketEvidence:
    """
    Verifies offline market evidence package according to Delta Sections 2.2, 4.1, 4.2.
    1. Checks manifest exact SHA-256 and exact schema_version.
    2. Checks exact SHA-256 and byte length for all six auxiliary artifacts and official sources.
    3. Verifies every listed ZIP and CSV file byte length and SHA-256 before parsing.
    4. Validates ZIP integrity (testzip).
    5. Strictly parses all CSV rows.
    6. Verifies no unlisted extra regular files or symlinks exist in the evidence package.
    7. Returns immutable VerifiedMarketEvidence with verified in-memory rows.
    """
    resolved_root = market_evidence_root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise MarketEvidenceInvalidError(
            f"market_evidence_invalid: not_a_directory: {market_evidence_root}"
        )

    manifest_p = resolved_root / "gap02_evidence_manifest.json"
    if not manifest_p.is_file() or manifest_p.is_symlink():
        raise MarketEvidenceInvalidError("market_evidence_invalid: manifest_missing")

    manifest_bytes = manifest_p.read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_sha != REVIEWED_MARKET_EVIDENCE_MANIFEST_SHA256:
        raise MarketEvidenceInvalidError(
            f"market_evidence_invalid: unapproved_market_evidence_identity: expected {REVIEWED_MARKET_EVIDENCE_MANIFEST_SHA256}, got {manifest_sha}"
        )

    try:
        manifest_data = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as exc:
        raise MarketEvidenceInvalidError(f"market_evidence_invalid: malformed_manifest: {exc}") from exc

    if manifest_data["schema_version"] != REVIEWED_MARKET_EVIDENCE_MANIFEST_SCHEMA_VERSION:
        raise MarketEvidenceInvalidError(
            f"market_evidence_invalid: manifest_schema_version_mismatch: {manifest_data['schema_version']}"
        )

    all_expected_files = {
        "gap02_evidence_manifest.json",
    }

    # Verify six auxiliary artifacts
    auxiliary_loaded: Dict[str, Any] = {}
    for rel_path, spec in AUXILIARY_ARTIFACT_SPECS.items():
        all_expected_files.add(rel_path)
        p = resolved_root / rel_path
        if not p.is_file() or p.is_symlink():
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: missing_auxiliary_artifact: {rel_path}"
            )
        data = p.read_bytes()
        if len(data) != spec["byte_length"]:
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: aux_byte_length_mismatch for {rel_path}: expected {spec['byte_length']}, got {len(data)}"
            )
        act_sha = hashlib.sha256(data).hexdigest()
        if act_sha != spec["sha256"]:
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: aux_sha256_mismatch for {rel_path}: expected {spec['sha256']}, got {act_sha}"
            )
        try:
            auxiliary_loaded[rel_path] = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: malformed_aux_json: {rel_path}: {exc}"
            ) from exc

    # Verify official sources
    for rel_path, spec in OFFICIAL_SOURCES_SPECS.items():
        all_expected_files.add(rel_path)
        p = resolved_root / rel_path
        if not p.is_file() or p.is_symlink():
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: missing_official_source: {rel_path}"
            )
        data = p.read_bytes()
        if len(data) != spec["byte_length"]:
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: official_source_byte_length_mismatch for {rel_path}: expected {spec['byte_length']}, got {len(data)}"
            )
        act_sha = hashlib.sha256(data).hexdigest()
        if act_sha != spec["sha256"]:
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: official_source_sha256_mismatch for {rel_path}: expected {spec['sha256']}, got {act_sha}"
            )

    artifacts = manifest_data["artifacts"]
    if not isinstance(artifacts, list):
        raise MarketEvidenceInvalidError("market_evidence_invalid: artifacts_not_list")

    seen_zip_paths = set()
    seen_csv_paths = set()
    all_csv_records: List[Dict[str, Any]] = []
    series_accum: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for art in artifacts:
        rel_zip = art["relative_zip_path"]
        if ".." in rel_zip or rel_zip.startswith("/"):
            raise MarketEvidenceInvalidError(f"market_evidence_invalid: path_traversal: {rel_zip}")
        if rel_zip in seen_zip_paths:
            raise MarketEvidenceInvalidError(f"market_evidence_invalid: duplicate_zip_path: {rel_zip}")
        seen_zip_paths.add(rel_zip)
        all_expected_files.add(rel_zip)

        zip_p = resolved_root / rel_zip
        if not zip_p.is_file() or zip_p.is_symlink():
            raise MarketEvidenceInvalidError(f"market_evidence_invalid: missing_zip_file: {rel_zip}")

        zip_bytes = zip_p.read_bytes()
        if len(zip_bytes) != art["zip_size_bytes"]:
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: zip_size_mismatch for {rel_zip}: expected {art['zip_size_bytes']}, got {len(zip_bytes)}"
            )
        zip_sha = hashlib.sha256(zip_bytes).hexdigest()
        if zip_sha != art["zip_sha256"]:
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: zip_hash_mismatch for {rel_zip}: expected {art['zip_sha256']}, got {zip_sha}"
            )

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                bad_file = zf.testzip()
                if bad_file is not None:
                    raise MarketEvidenceInvalidError(f"market_evidence_invalid: corrupt_zip: {rel_zip}")
        except Exception as exc:
            raise MarketEvidenceInvalidError(f"market_evidence_invalid: corrupt_zip: {rel_zip}: {exc}") from exc

        csv_records = art["csv_records"]
        if not isinstance(csv_records, list):
            raise MarketEvidenceInvalidError(f"market_evidence_invalid: csv_records_not_list in {rel_zip}")

        for c_rec in csv_records:
            rel_csv = c_rec["relative_csv_path"]
            if ".." in rel_csv or rel_csv.startswith("/"):
                raise MarketEvidenceInvalidError(f"market_evidence_invalid: path_traversal: {rel_csv}")
            if rel_csv in seen_csv_paths:
                raise MarketEvidenceInvalidError(f"market_evidence_invalid: duplicate_csv_path: {rel_csv}")
            seen_csv_paths.add(rel_csv)
            all_expected_files.add(rel_csv)

            csv_p = resolved_root / rel_csv
            if not csv_p.is_file() or csv_p.is_symlink():
                raise MarketEvidenceInvalidError(f"market_evidence_invalid: missing_csv_file: {rel_csv}")

            csv_bytes = csv_p.read_bytes()
            if len(csv_bytes) != c_rec["csv_size_bytes"]:
                raise MarketEvidenceInvalidError(
                    f"market_evidence_invalid: csv_size_mismatch for {rel_csv}: expected {c_rec['csv_size_bytes']}, got {len(csv_bytes)}"
                )
            csv_sha = hashlib.sha256(csv_bytes).hexdigest()
            if csv_sha != c_rec["csv_sha256"]:
                raise MarketEvidenceInvalidError(
                    f"market_evidence_invalid: csv_hash_mismatch for {rel_csv}: expected {c_rec['csv_sha256']}, got {csv_sha}"
                )

            # Strict parse CSV rows
            parsed_rows = parse_strict_csv(csv_bytes, art["rel_category"])
            all_csv_records.append(c_rec)

            filename = c_rec["csv_filename"]
            symbol = filename.split("-")[0]
            family = resolve_csv_family(art["rel_category"])
            series_accum[(family, symbol)].extend(parsed_rows)

    # Check for unlisted extra files or symlinks on disk
    for fpath in resolved_root.rglob("*"):
        if fpath.is_symlink():
            raise MarketEvidenceInvalidError(
                f"market_evidence_invalid: symlink_forbidden: {fpath.relative_to(resolved_root)}"
            )
        if fpath.is_file():
            rel = str(fpath.relative_to(resolved_root))
            if rel not in all_expected_files:
                raise MarketEvidenceInvalidError(
                    f"market_evidence_invalid: unlisted_extra_path: {rel}"
                )

    # Sort each series deterministically by timestamp key
    series_final: Dict[Tuple[str, str], Tuple[Dict[str, Any], ...]] = {}
    timestamp_keys = {
        "klines_1h": "open_time",
        "klines_1m": "open_time",
        "mark_price_1h": "open_time",
        "index_price_1h": "open_time",
        "premium_index_1h": "open_time",
        "metrics_5m": "create_time",
        "funding_rate": "calc_time",
        "book_depth": "timestamp",
        "agg_trades": "transact_time",
    }
    for (fam, sym), row_list in series_accum.items():
        ts_key = timestamp_keys[fam]
        sorted_rows = sorted(row_list, key=lambda r: r[ts_key])
        series_final[(fam, sym)] = tuple(sorted_rows)

    return VerifiedMarketEvidence(
        manifest_sha256=manifest_sha,
        manifest_byte_length=len(manifest_bytes),
        manifest_data=manifest_data,
        auxiliary_artifacts=auxiliary_loaded,
        csv_records=tuple(all_csv_records),
        series_by_symbol_and_type=series_final,
    )
