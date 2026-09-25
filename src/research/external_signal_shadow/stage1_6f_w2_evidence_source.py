"""Stage 1.6F-W2 historical price evidence source and strict loader core.

Invariants: INV-W2E01, INV-W2E02, INV-W2E03, INV-W2E10, INV-W2E13.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

from configs.base import (
    EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES,
    EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES,
    EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES,
)
from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import (
    CandidateEvidenceSourceError,
    VerifiedCandidateEvidence,
    compute_logical_archive_record_id,
    compute_physical_source_object_id,
    load_verified_candidate_evidence,
    parse_and_validate_csv,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    reconstruct_denominator,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    VerifiedCInput,
    verify_c_input,
)


class W2EvidenceSourceError(Exception):
    """Exception raised when W2 evidence fails validation, authority, or contract gates."""
    pass


W2_SCHEMA_VERSION = "stage1_6f_w2_historical_price_candidate_manifest_v1"
W2_NETWORK_AUTH_SCHEMA = "stage1_6f_w2_network_authorization_v1"

ALL_URLS_SHA256 = "3b9ab69a8c1236cab59f161636ae9e4136465ca599d735ef65e37fd2cc574a46"
REUSE_URLS_SHA256 = "9773f11e316ce480651b0debf6258fefbd39a1ee9bdc2d6bdd838484704ed405"
FETCH_URLS_SHA256 = "6eac006f8854a17a2d78b4306c03da6f28528aba58ffcfafd6b5f078d4ed7058"

FROZEN_EXPANSION_DESIGN_PATH = "docs/designs/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-design_CN.md"
FROZEN_EXPANSION_DESIGN_SHA = "1119eb86811ad5aa8e5e54943c5d8e41bfd389625df77ff631774b6cf97dbfd4"

FROZEN_EXPANSION_PLAN_PATH = "docs/plans/2026-09-16-external-signal-shadow-lab-stage1-6f-historical-evidence-package-expansion-implementation-plan_CN.md"
FROZEN_EXPANSION_PLAN_SHA = "fb13fb3388ed979c23bc5cf964b500388c0c20658bf0038d00bb0ae9fabac27d"

FROZEN_NETWORK_AUTH_PATH = "configs/authorizations/network_auth_expansion_run_20260917_002.json"
FROZEN_NETWORK_AUTH_SHA = "8df4a49bb97efbb0b7a7e69f741ae25d2dbfb12b53cb760d6c0052b8b05dbff6"

FROZEN_MATRIX_SHA = "b6318d38f37171976e554b74f99adbe5f92f49ed4b389fa433401752cc6254a8"

W2_13_FALSE_FLAGS: Dict[str, bool] = {
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

PERMITTED_METRICS = {"klines_1h", "index_price_1h", "mark_price_1h"}


def canonical_json_bytes(obj: Any) -> bytes:
    """Canonical UTF-8 compact JSON bytes."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def canonical_json_sha256(obj: Any) -> str:
    """Canonical SHA-256 of canonical JSON bytes."""
    return hashlib.sha256(canonical_json_bytes(obj)).hexdigest()


@dataclass(frozen=True)
class W2AuthorityInputs:
    project_root: Path
    verified_c: VerifiedCInput
    verified_002: VerifiedCandidateEvidence
    denominator_records: tuple[dict[str, object], ...]
    distinct_parent_count: int
    window_defined_count: int
    window_parent_count: int
    settlement_time_unproven_count: int
    coverage_matrix_path: Path
    selected_matrix_records: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class W2RequestSet:
    denominator_records: tuple[dict[str, object], ...]
    logical_records: tuple[dict[str, object], ...]
    physical_records: tuple[dict[str, object], ...]
    reuse_ids: frozenset[str]
    fetch_ids: frozenset[str]
    all_urls_sha256: str
    reuse_urls_sha256: str
    fetch_urls_sha256: str


def derive_w2_authority_inputs(
    *,
    project_root: Path,
    c_completed_root: Path,
    b_source_export: Path,
    canonical_002_root: Path,
    coverage_matrix: Path,
    approved_design_path: Path,
    approved_design_sha: str,
    approved_plan_path: Path,
    approved_plan_sha: str,
    network_authorization_path: Path,
    network_authorization_sha: str,
) -> W2AuthorityInputs:
    """Derive verified W2 authority inputs, cohort, and frozen request metadata."""
    # 1. Verify Design & Plan bytes
    if not approved_design_path.is_file():
        raise W2EvidenceSourceError(f"STOP=approved_authority_mismatch:design_missing:{approved_design_path}")
    design_bytes = approved_design_path.read_bytes()
    actual_design_sha = hashlib.sha256(design_bytes).hexdigest()
    if actual_design_sha != approved_design_sha:
        raise W2EvidenceSourceError(
            f"STOP=approved_authority_mismatch:design_sha:{actual_design_sha}!={approved_design_sha}"
        )

    if not approved_plan_path.is_file():
        raise W2EvidenceSourceError(f"STOP=approved_authority_mismatch:plan_missing:{approved_plan_path}")
    plan_bytes = approved_plan_path.read_bytes()
    actual_plan_sha = hashlib.sha256(plan_bytes).hexdigest()
    if actual_plan_sha != approved_plan_sha:
        raise W2EvidenceSourceError(
            f"STOP=approved_authority_mismatch:plan_sha:{actual_plan_sha}!={approved_plan_sha}"
        )

    # 2. Check coverage_matrix first
    if not coverage_matrix.is_file() or coverage_matrix.is_symlink():
        raise W2EvidenceSourceError(f"STOP=w2_request_set_mismatch:matrix_missing_or_symlink:{coverage_matrix}")
    matrix_bytes = coverage_matrix.read_bytes()
    actual_matrix_sha = hashlib.sha256(matrix_bytes).hexdigest()
    if actual_matrix_sha != FROZEN_MATRIX_SHA:
        raise W2EvidenceSourceError(
            f"STOP=w2_request_set_mismatch:matrix_sha_mismatch:{actual_matrix_sha}!={FROZEN_MATRIX_SHA}"
        )

    # 3. Verify C input and 002 candidate evidence
    verified_c = verify_c_input(
        project_root=project_root,
        completed_root=c_completed_root,
        source_export=b_source_export,
    )
    if not verified_c:
        raise W2EvidenceSourceError("STOP=canonical_c_authority_invalid")

    try:
        verified_002 = load_verified_candidate_evidence(
            project_root=project_root,
            candidate_root=canonical_002_root,
            approved_design_path=project_root / FROZEN_EXPANSION_DESIGN_PATH,
            approved_design_sha=FROZEN_EXPANSION_DESIGN_SHA,
            approved_plan_path=project_root / FROZEN_EXPANSION_PLAN_PATH,
            approved_plan_sha=FROZEN_EXPANSION_PLAN_SHA,
            network_authorization_path=project_root / FROZEN_NETWORK_AUTH_PATH,
            network_authorization_sha=FROZEN_NETWORK_AUTH_SHA,
        )
    except CandidateEvidenceSourceError as exc:
        raise W2EvidenceSourceError(f"STOP=w2_request_set_mismatch:002_evidence_invalid:{exc}") from exc

    # 4. Derive denominator cohort and verify exact match with verified 002
    denominator_rows = reconstruct_denominator(verified_c)
    matrix_data = json.loads(matrix_bytes.decode("utf-8"))
    in_range_records = matrix_data.get("in_range_archive_records", [])
    in_range_symbols = {r["symbol"] for r in in_range_records if "symbol" in r}

    eligible_symbols = {r.symbol for r in denominator_rows if r.eligibility_passed}
    cohort_symbols = sorted((eligible_symbols & in_range_symbols) - {"REEFUSDT"})
    if len(cohort_symbols) != 41:
        raise W2EvidenceSourceError(
            f"STOP=w2_denominator_authority_invalid:expected 41 symbols, got {len(cohort_symbols)}"
        )

    verified_002_cohort_symbols = list(verified_002.cohort)
    if cohort_symbols != verified_002_cohort_symbols:
        raise W2EvidenceSourceError("STOP=w2_denominator_mismatch_with_canonical_002")

    # 5. Map cohort identities and temporal status
    cohort_rows_by_symbol = {r.symbol: r for r in denominator_rows if r.symbol in set(cohort_symbols)}
    parent_ids = {r.parent_article_id for r in cohort_rows_by_symbol.values()}
    distinct_parent_count = len(parent_ids)
    if distinct_parent_count != 27:
        raise W2EvidenceSourceError(
            f"STOP=w2_denominator_authority_invalid:expected 27 distinct parents, got {distinct_parent_count}"
        )

    # 6. Temporal derivation for all 41 contracts
    denominator_records: List[Dict[str, Any]] = []
    window_defined_symbols: Set[str] = set()
    window_parent_ids: Set[str] = set()
    settlement_time_unproven_count = 0

    for sym in cohort_symbols:
        r = cohort_rows_by_symbol[sym]
        t_pub_ms = r.t_pub_ms
        if t_pub_ms is None or t_pub_ms <= 0:
            raise W2EvidenceSourceError(f"STOP=w2_temporal_authority_invalid:pub_not_present:{sym}")

        t_settle_ms = r.t_settle_ms
        if t_settle_ms is not None:
            if not isinstance(t_settle_ms, int) or t_settle_ms <= 0:
                raise W2EvidenceSourceError(f"STOP=w2_temporal_authority_invalid:invalid_t_settle:{sym}")
            if t_settle_ms <= t_pub_ms:
                raise W2EvidenceSourceError(f"STOP=w2_temporal_authority_invalid:t_settle_le_t_pub:{sym}")

            nominal_start_ms = t_settle_ms - 86_400_000
            window_start_ms = max(t_pub_ms, nominal_start_ms)
            window_end_ms = t_settle_ms
            is_truncated = (window_start_ms > nominal_start_ms)
            temporal_status = "window_defined"

            window_defined_symbols.add(sym)
            window_parent_ids.add(r.parent_article_id)
        else:
            nominal_start_ms = None
            window_start_ms = None
            window_end_ms = None
            is_truncated = None
            temporal_status = "settlement_time_unproven"
            settlement_time_unproven_count += 1

        denom_record = {
            "parent_article_id": r.parent_article_id,
            "contract_id": r.contract_id,
            "canonical_symbol": r.symbol,
            "symbol": r.symbol,
            "t_pub_ms": t_pub_ms,
            "t_settle_ms": t_settle_ms,
            "temporal_status": temporal_status,
            "nominal_window_start_ms": nominal_start_ms,
            "window_start_ms": window_start_ms,
            "window_end_ms": window_end_ms,
            "is_truncated_by_tpub": is_truncated,
        }
        denominator_records.append(denom_record)

    denominator_records.sort(
        key=lambda x: (x["parent_article_id"], x["contract_id"], x["canonical_symbol"])
    )

    window_defined_count = len(window_defined_symbols)
    window_parent_count = len(window_parent_ids)

    if window_defined_count != 31 or settlement_time_unproven_count != 10 or window_parent_count != 21:
        raise W2EvidenceSourceError(
            f"STOP=w2_temporal_authority_invalid:counts_mismatch:defined={window_defined_count},"
            f"unproven={settlement_time_unproven_count},parents={window_parent_count}"
        )

    # 6. Select exact 180 matrix records for the 31 window-defined symbols
    selected_matrix_records: List[Dict[str, Any]] = []
    for r in in_range_records:
        if "symbol" not in r or "window" not in r or "metric" not in r or "url" not in r:
            raise W2EvidenceSourceError("STOP=w2_request_set_mismatch:missing_record_field")
        sym = r["symbol"]
        win = r["window"]
        met = r["metric"]
        if sym in window_defined_symbols and win == "w2_settlement_24h" and met in PERMITTED_METRICS:
            # Validate URL sanity
            url = r["url"]
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                raise W2EvidenceSourceError(f"STOP=w2_request_set_mismatch:non_https_url:{url}")
            if parsed.query or parsed.fragment or parsed.username or parsed.password:
                raise W2EvidenceSourceError(f"STOP=w2_request_set_mismatch:url_has_query_or_userinfo:{url}")
            if parsed.port not in (None, 443):
                raise W2EvidenceSourceError(f"STOP=w2_request_set_mismatch:non_443_port:{url}")
            if parsed.netloc != "s3-ap-northeast-1.amazonaws.com" or not parsed.path.startswith("/data.binance.vision/"):
                raise W2EvidenceSourceError(f"STOP=w2_request_set_mismatch:unauthorized_host:{url}")

            selected_matrix_records.append(r)

    selected_matrix_records.sort(
        key=lambda x: (
            x["parent_article_id"],
            x["contract_id"],
            x["symbol"],
            x["window"],
            x["metric"],
            x["archive_date_or_month"],
        )
    )

    if len(selected_matrix_records) != 180:
        raise W2EvidenceSourceError(
            f"STOP=w2_request_set_mismatch:expected 180 records, got {len(selected_matrix_records)}"
        )

    # 7. Validate URL sets and hashes
    all_urls = sorted({r["url"] for r in selected_matrix_records})
    if len(all_urls) != 180:
        raise W2EvidenceSourceError(f"STOP=w2_request_set_mismatch:url_count_mismatch:{len(all_urls)}")

    actual_all_urls_sha = canonical_json_sha256(all_urls)
    if actual_all_urls_sha != ALL_URLS_SHA256:
        raise W2EvidenceSourceError(
            f"STOP=w2_request_set_mismatch:all_urls_sha_mismatch:{actual_all_urls_sha}!={ALL_URLS_SHA256}"
        )

    # 002 physical URL set
    verified_002_urls = {obj["exact_source_url"] for obj in verified_002.manifest["physical_source_objects"]}
    reuse_urls = sorted(set(all_urls) & verified_002_urls)
    fetch_urls = sorted(set(all_urls) - verified_002_urls)

    if len(reuse_urls) != 9:
        raise W2EvidenceSourceError(f"STOP=w2_request_set_mismatch:reuse_count_mismatch:{len(reuse_urls)}!=9")
    if len(fetch_urls) != 171:
        raise W2EvidenceSourceError(f"STOP=w2_request_set_mismatch:fetch_count_mismatch:{len(fetch_urls)}!=171")

    actual_reuse_sha = canonical_json_sha256(reuse_urls)
    if actual_reuse_sha != REUSE_URLS_SHA256:
        raise W2EvidenceSourceError(
            f"STOP=w2_request_set_mismatch:reuse_urls_sha_mismatch:{actual_reuse_sha}!={REUSE_URLS_SHA256}"
        )

    actual_fetch_sha = canonical_json_sha256(fetch_urls)
    if actual_fetch_sha != FETCH_URLS_SHA256:
        raise W2EvidenceSourceError(
            f"STOP=w2_request_set_mismatch:fetch_urls_sha_mismatch:{actual_fetch_sha}!={FETCH_URLS_SHA256}"
        )

    return W2AuthorityInputs(
        project_root=project_root,
        verified_c=verified_c,
        verified_002=verified_002,
        denominator_records=tuple(denominator_records),
        distinct_parent_count=distinct_parent_count,
        window_defined_count=window_defined_count,
        window_parent_count=window_parent_count,
        settlement_time_unproven_count=settlement_time_unproven_count,
        coverage_matrix_path=coverage_matrix,
        selected_matrix_records=tuple(selected_matrix_records),
    )


def derive_w2_request_set(authority: W2AuthorityInputs) -> W2RequestSet:
    """Derive frozen W2 metadata only; never inspect/output price outcomes."""
    logical_records: List[Dict[str, Any]] = []
    physical_records_map: Dict[str, Dict[str, Any]] = {}

    verified_002_urls = {
        obj["exact_source_url"]: obj for obj in authority.verified_002.manifest["physical_source_objects"]
    }

    for r in authority.selected_matrix_records:
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

        matrix_record_projection_v1 = {
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
        }

        logical_entry = {
            "logical_archive_record_id": logical_id,
            "matrix_record_sha256": matrix_record_sha,
            "matrix_record_projection_v1": matrix_record_projection_v1,
            "physical_source_object_id": physical_id,
            "record_state": "unfetched",
        }
        logical_records.append(logical_entry)

        if physical_id not in physical_records_map:
            is_reuse = exact_source_url in verified_002_urls
            physical_entry = {
                "physical_source_object_id": physical_id,
                "exact_source_url": exact_source_url,
                "acquisition_method": "copied_verified_002" if is_reuse else "network_get",
                "source_manifest_sha256": (
                    authority.verified_002.manifest["candidate_manifest_sha256"]
                    if is_reuse and "candidate_manifest_sha256" in authority.verified_002.manifest
                    else None
                ),
                "source_physical_source_object_id": physical_id if is_reuse else None,
                "network_attempt_count": 0 if is_reuse else 1,
            }
            physical_records_map[physical_id] = physical_entry

    logical_records.sort(key=lambda x: str(x["logical_archive_record_id"]))
    physical_records = sorted(physical_records_map.values(), key=lambda x: str(x["physical_source_object_id"]))

    reuse_ids = frozenset(
        p["physical_source_object_id"] for p in physical_records if p["acquisition_method"] == "copied_verified_002"
    )
    fetch_ids = frozenset(
        p["physical_source_object_id"] for p in physical_records if p["acquisition_method"] == "network_get"
    )

    all_urls = sorted({r["url"] for r in authority.selected_matrix_records})
    reuse_urls = sorted(r["url"] for r in authority.selected_matrix_records if r["url"] in verified_002_urls)
    reuse_urls = sorted(set(reuse_urls))
    fetch_urls = sorted(r["url"] for r in authority.selected_matrix_records if r["url"] not in verified_002_urls)
    fetch_urls = sorted(set(fetch_urls))

    return W2RequestSet(
        denominator_records=authority.denominator_records,
        logical_records=tuple(logical_records),
        physical_records=tuple(physical_records),
        reuse_ids=reuse_ids,
        fetch_ids=fetch_ids,
        all_urls_sha256=canonical_json_sha256(all_urls),
        reuse_urls_sha256=canonical_json_sha256(reuse_urls),
        fetch_urls_sha256=canonical_json_sha256(fetch_urls),
    )


def validate_w2_network_authorization(
    *,
    authorization_path: Path,
    authorization_sha256: str,
    design_path: Path,
    design_sha256: str,
    plan_path: Path,
    plan_sha256: str,
    run_id: str,
    request_set: W2RequestSet,
) -> dict[str, object]:
    """Require exact one-time W2 authorization; never create it."""
    if not authorization_path.is_file():
        raise W2EvidenceSourceError(
            f"STOP=w2_network_authorization_invalid:file_missing:{authorization_path}"
        )

    auth_bytes = authorization_path.read_bytes()
    actual_sha = hashlib.sha256(auth_bytes).hexdigest()
    if actual_sha != authorization_sha256:
        raise W2EvidenceSourceError(
            f"STOP=w2_network_authorization_invalid:sha_mismatch:{actual_sha}!={authorization_sha256}"
        )

    try:
        data = json.loads(auth_bytes.decode("utf-8"))
    except Exception as e:
        raise W2EvidenceSourceError(f"STOP=w2_network_authorization_invalid:bad_json:{e}") from e

    expected_keys = {
        "schema_version",
        "run_id",
        "design_sha256",
        "plan_sha256",
        "all_urls_sha256",
        "reuse_urls_sha256",
        "fetch_urls_sha256",
        "max_requests",
        "public_archive_get_allowed",
        "permission_flags",
    }
    if set(data.keys()) != expected_keys:
        raise W2EvidenceSourceError(
            f"STOP=w2_network_authorization_invalid:keys_mismatch:{sorted(data.keys())}"
        )

    if data["schema_version"] != W2_NETWORK_AUTH_SCHEMA:
        raise W2EvidenceSourceError(
            f"STOP=w2_network_authorization_invalid:schema_version:{data['schema_version']}"
        )

    if data["run_id"] != run_id or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,95}$", run_id):
        raise W2EvidenceSourceError(
            f"STOP=w2_network_authorization_invalid:run_id_mismatch:{data['run_id']}!={run_id}"
        )

    if data["design_sha256"] != design_sha256:
        raise W2EvidenceSourceError(
            f"STOP=w2_network_authorization_invalid:design_sha_mismatch:{data['design_sha256']}!={design_sha256}"
        )

    if data["plan_sha256"] != plan_sha256:
        raise W2EvidenceSourceError(
            f"STOP=w2_network_authorization_invalid:plan_sha_mismatch:{data['plan_sha256']}!={plan_sha256}"
        )

    if data["all_urls_sha256"] != request_set.all_urls_sha256:
        raise W2EvidenceSourceError(
            "STOP=w2_network_authorization_invalid:all_urls_sha_mismatch"
        )

    if data["reuse_urls_sha256"] != request_set.reuse_urls_sha256:
        raise W2EvidenceSourceError(
            "STOP=w2_network_authorization_invalid:reuse_urls_sha_mismatch"
        )

    if data["fetch_urls_sha256"] != request_set.fetch_urls_sha256:
        raise W2EvidenceSourceError(
            "STOP=w2_network_authorization_invalid:fetch_urls_sha_mismatch"
        )

    if data["max_requests"] != 171:
        raise W2EvidenceSourceError(
            f"STOP=w2_network_authorization_invalid:max_requests_must_be_171:{data['max_requests']}"
        )

    if data["public_archive_get_allowed"] is not True:
        raise W2EvidenceSourceError(
            "STOP=w2_network_authorization_invalid:public_archive_get_not_allowed"
        )

    perm_flags = data.get("permission_flags", {})
    if not isinstance(perm_flags, dict) or set(perm_flags.keys()) != set(W2_13_FALSE_FLAGS.keys()):
        raise W2EvidenceSourceError(
            "STOP=w2_network_authorization_invalid:permission_flags_keys_mismatch"
        )

    for k, expected_v in W2_13_FALSE_FLAGS.items():
        actual_v = perm_flags.get(k)
        if actual_v is not expected_v or type(actual_v) is not bool:
            raise W2EvidenceSourceError(
                f"STOP=w2_network_authorization_invalid:permission_flag_violation:{k}={actual_v}"
            )

    return data


@dataclass(frozen=True)
class VerifiedW2Evidence:
    run_id: str
    completed_root: Path
    manifest: dict[str, object]
    denominator_records: tuple[dict[str, object], ...]
    logical_archive_records: tuple[dict[str, object], ...]
    physical_source_objects: tuple[dict[str, object], ...]
    metric_window_coverages: tuple[dict[str, object], ...]
    candidate_root_state: str


def compute_w2_grid_points(
    window_start_ms: int,
    window_end_ms: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Compute (G, C) open and complete-bar UTC hour grids for a given interval."""
    H = 3_600_000
    if window_end_ms <= window_start_ms:
        return (), ()

    rem = window_start_ms % H
    first_open = window_start_ms if rem == 0 else window_start_ms + (H - rem)

    g_points: list[int] = []
    c_points: list[int] = []
    t = first_open
    while t < window_end_ms:
        g_points.append(t)
        if t + H <= window_end_ms:
            c_points.append(t)
        t += H

    return tuple(g_points), tuple(c_points)


def validate_w2_csv_content(
    csv_source: bytes | Path,
    url: str,
) -> tuple[bool, str, list[dict[str, Any]], str | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Validate extracted CSV content strictly according to W2 rules without outputting prices."""
    if isinstance(csv_source, bytes):
        if not csv_source:
            return False, "empty_csv", [], None, None, None
        if len(csv_source) > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES:
            return False, f"csv_byte_length_exceeded:{len(csv_source)}", [], None, None, None
    elif isinstance(csv_source, Path):
        if not csv_source.is_file():
            return False, "file_missing", [], None, None, None
        size = csv_source.stat().st_size
        if size == 0:
            return False, "empty_csv", [], None, None, None
        if size > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES:
            return False, f"csv_byte_length_exceeded:{size}", [], None, None, None
    else:
        return False, f"unsupported_csv_source_type:{type(csv_source)}", [], None, None, None

    if "/markPriceKlines/" in url:
        family = "mark_price_1h"
    elif "/indexPriceKlines/" in url:
        family = "index_price_1h"
    elif "/klines/" in url:
        family = "klines_1h"
    else:
        return False, f"unknown_family_url:{url}", [], None, None, None

    m = re.search(r"-1h-(\d{4}-\d{2}-\d{2})\.(?:zip|csv)$", url)
    if not m:
        return False, f"invalid_date_in_url:{url}", [], None, None, None
    expected_date = m.group(1)

    status, reason, raw_header, _, _, _, parsed_rows = parse_and_validate_csv(
        family=family,
        csv_source=csv_source,
    )
    if status != "fetched_verified":
        return False, f"parse_error:{reason}", [], raw_header, None, None

    if len(parsed_rows) == 0:
        return False, "header_only_csv", [], raw_header, None, None

    prev_open_time = None
    for row in parsed_rows:
        open_time = row["open_time"]
        close_time = row["close_time"]

        if open_time % 3_600_000 != 0:
            return False, f"open_time_not_hourly:{open_time}", [], raw_header, None, None

        if close_time != open_time + 3_600_000 - 1:
            return False, f"close_time_mismatch:{close_time}!={open_time + 3_600_000 - 1}", [], raw_header, None, None

        dt = datetime.datetime.fromtimestamp(open_time / 1000, tz=timezone.utc)
        row_date = dt.strftime("%Y-%m-%d")
        if row_date != expected_date:
            return False, f"open_time_date_mismatch:{row_date}!={expected_date}", [], raw_header, None, None

        if prev_open_time is not None and open_time <= prev_open_time:
            return False, f"duplicate_or_decreasing_open_time:{open_time}<={prev_open_time}", [], raw_header, None, None
        prev_open_time = open_time

    return True, "ok", parsed_rows, raw_header, parsed_rows[0], parsed_rows[-1]


def validate_w2_zip_and_csv(
    zip_path: Path,
    csv_path: Path,
    expected_url: str,
) -> dict[str, Any]:
    """Validate on-disk ZIP and CSV files with member matching and streaming cap."""
    if zip_path.is_symlink() or not zip_path.is_file():
        raise W2EvidenceSourceError(f"w2_root_invalid:zip_not_regular_file:{zip_path}")
    if csv_path.is_symlink() or not csv_path.is_file():
        raise W2EvidenceSourceError(f"w2_root_invalid:csv_not_regular_file:{csv_path}")

    # Stream zip to check byte length and hash
    zip_hasher = hashlib.sha256()
    zip_len = 0
    with open(zip_path, "rb") as zf_in:
        while True:
            remaining = EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES - zip_len
            to_read = min(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES, remaining)
            if to_read <= 0:
                if zf_in.read(1):
                    raise W2EvidenceSourceError("w2_root_invalid:zip_length_exceeded")
                break
            chunk = zf_in.read(to_read)
            if not chunk:
                break
            zip_hasher.update(chunk)
            zip_len += len(chunk)
            if zip_len > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES:
                raise W2EvidenceSourceError("w2_root_invalid:zip_length_exceeded")

    # Stream csv to check byte length and hash
    csv_hasher = hashlib.sha256()
    csv_len = 0
    with open(csv_path, "rb") as cf_in:
        while True:
            remaining = EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES - csv_len
            to_read = min(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES, remaining)
            if to_read <= 0:
                if cf_in.read(1):
                    raise W2EvidenceSourceError("w2_root_invalid:csv_length_exceeded")
                break
            chunk = cf_in.read(to_read)
            if not chunk:
                break
            csv_hasher.update(chunk)
            csv_len += len(chunk)
            if csv_len > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES:
                raise W2EvidenceSourceError("w2_root_invalid:csv_length_exceeded")

    expected_zip_basename = expected_url.split("/")[-1]
    expected_csv_member = expected_zip_basename[:-4] + ".csv" if expected_zip_basename.endswith(".zip") else expected_zip_basename

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            infolist = zf.infolist()
            if len(infolist) != 1:
                raise W2EvidenceSourceError(f"w2_root_invalid:zip_member_count:{len(infolist)}!=1")
            info = infolist[0]
            if info.is_dir() or (info.external_attr >> 16 & 0o120000 == 0o120000):
                raise W2EvidenceSourceError(f"w2_root_invalid:zip_member_not_regular:{info.filename}")
            if info.filename != expected_csv_member:
                raise W2EvidenceSourceError(f"w2_root_invalid:zip_member_name:{info.filename}!={expected_csv_member}")
            if info.file_size > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES:
                raise W2EvidenceSourceError(f"w2_root_invalid:zip_uncompressed_length_exceeded:{info.file_size}")

            # Stream compare zip member with csv_path in chunks
            with zf.open(info, "r") as mf, open(csv_path, "rb") as cf:
                while True:
                    m_chunk = mf.read(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES)
                    c_chunk = cf.read(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES)
                    if m_chunk != c_chunk:
                        raise W2EvidenceSourceError(f"w2_root_invalid:zip_csv_content_mismatch:{zip_path}")
                    if not m_chunk:
                        break
    except zipfile.BadZipFile as exc:
        raise W2EvidenceSourceError(f"w2_root_invalid:bad_zip_file:{exc}") from exc

    valid, reason, parsed_rows, header, first_row, last_row = validate_w2_csv_content(csv_path, expected_url)
    if not valid:
        if "duplicate" in reason:
            raise W2EvidenceSourceError(f"w2_root_invalid:hour_grid:{reason}")
        raise W2EvidenceSourceError(f"w2_root_invalid:csv_invalid:{reason}")

    return {
        "zip_sha256": zip_hasher.hexdigest(),
        "zip_byte_length": zip_len,
        "csv_sha256": csv_hasher.hexdigest(),
        "csv_byte_length": csv_len,
        "zip_member_name": expected_csv_member,
        "csv_header": header,
        "csv_row_count": len(parsed_rows),
        "first_row": first_row,
        "last_row": last_row,
        "parsed_rows": parsed_rows,
    }


def compute_w2_metric_coverages(
    denominator_records: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    logical_records: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    physical_records_map: dict[str, dict[str, Any]],
    loaded_csv_rows: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], ...]:
    """Compute exactly 123 metric window coverage records."""
    metrics = ("klines_1h", "index_price_1h", "mark_price_1h")
    logical_by_identity_metric: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for log_rec in logical_records:
        proj = log_rec["matrix_record_projection_v1"]
        key = (
            proj["parent_article_id"],
            proj["contract_id"],
            proj["canonical_symbol"],
            proj["metric"],
        )
        if key not in logical_by_identity_metric:
            logical_by_identity_metric[key] = []
        logical_by_identity_metric[key].append(log_rec)

    coverages: list[dict[str, Any]] = []

    for denom in denominator_records:
        parent_id = denom["parent_article_id"]
        contract_id = denom["contract_id"]
        canonical_symbol = denom["canonical_symbol"]
        temporal_status = denom["temporal_status"]

        for met in metrics:
            key = (parent_id, contract_id, canonical_symbol, met)
            log_recs = sorted(
                logical_by_identity_metric.get(key, []),
                key=lambda x: x["logical_archive_record_id"],
            )
            log_ids = [r["logical_archive_record_id"] for r in log_recs]

            if temporal_status == "settlement_time_unproven":
                cov = {
                    "parent_article_id": parent_id,
                    "contract_id": contract_id,
                    "canonical_symbol": canonical_symbol,
                    "metric": met,
                    "window_start_ms": None,
                    "window_end_ms": None,
                    "logical_archive_record_ids": [],
                    "expected_open_count": None,
                    "observed_open_count": None,
                    "missing_open_count": None,
                    "raw_open_grid_status": "temporal_unproven",
                    "expected_complete_bar_count": None,
                    "observed_complete_bar_count": None,
                    "missing_complete_bar_count": None,
                    "complete_bar_status": "temporal_unproven",
                    "zero_index_close_count": None,
                }
                coverages.append(cov)
                continue

            window_start_ms = denom["window_start_ms"]
            window_end_ms = denom["window_end_ms"]
            assert isinstance(window_start_ms, int) and isinstance(window_end_ms, int)

            G, C = compute_w2_grid_points(window_start_ms, window_end_ms)
            expected_open_count = len(G)
            expected_complete_bar_count = len(C)

            all_physical_verified = True
            for r in log_recs:
                phys_id = r["physical_source_object_id"]
                phys = physical_records_map.get(phys_id)
                if not phys or phys.get("fetch_status") != "fetched_verified":
                    all_physical_verified = False
                    break

            if not all_physical_verified:
                cov = {
                    "parent_article_id": parent_id,
                    "contract_id": contract_id,
                    "canonical_symbol": canonical_symbol,
                    "metric": met,
                    "window_start_ms": window_start_ms,
                    "window_end_ms": window_end_ms,
                    "logical_archive_record_ids": log_ids,
                    "expected_open_count": expected_open_count,
                    "observed_open_count": None,
                    "missing_open_count": None,
                    "raw_open_grid_status": "not_proven",
                    "expected_complete_bar_count": expected_complete_bar_count,
                    "observed_complete_bar_count": None,
                    "missing_complete_bar_count": None,
                    "complete_bar_status": "not_proven",
                    "zero_index_close_count": None,
                }
                coverages.append(cov)
                continue

            aggregated_rows: list[dict[str, Any]] = []
            for r in log_recs:
                phys_id = r["physical_source_object_id"]
                aggregated_rows.extend(loaded_csv_rows.get(phys_id, []))

            rows_by_open: dict[int, dict[str, Any]] = {}
            for row in aggregated_rows:
                ot = row["open_time"]
                rows_by_open[ot] = row

            g_set = set(G)
            c_set = set(C)

            observed_open_points = {ot for ot in rows_by_open if ot in g_set}
            observed_open_count = len(observed_open_points)
            missing_open_count = len(g_set - observed_open_points)

            if len(G) == 0:
                raw_open_grid_status = "no_expected_points"
            elif missing_open_count == 0:
                raw_open_grid_status = "observed"
            else:
                raw_open_grid_status = "incomplete"

            observed_complete_points = {ot for ot in rows_by_open if ot in c_set}
            observed_complete_bar_count = len(observed_complete_points)
            missing_complete_bar_count = len(c_set - observed_complete_points)

            if len(C) == 0:
                complete_bar_status = "no_complete_bars"
            elif missing_complete_bar_count == 0:
                complete_bar_status = "observed"
            else:
                complete_bar_status = "incomplete"

            if met == "index_price_1h":
                zero_count = 0
                for ot in observed_complete_points:
                    if float(rows_by_open[ot]["close"]) == 0.0:
                        zero_count += 1
                zero_index_close_count = zero_count
            else:
                zero_index_close_count = None

            cov = {
                "parent_article_id": parent_id,
                "contract_id": contract_id,
                "canonical_symbol": canonical_symbol,
                "metric": met,
                "window_start_ms": window_start_ms,
                "window_end_ms": window_end_ms,
                "logical_archive_record_ids": log_ids,
                "expected_open_count": expected_open_count,
                "observed_open_count": observed_open_count,
                "missing_open_count": missing_open_count,
                "raw_open_grid_status": raw_open_grid_status,
                "expected_complete_bar_count": expected_complete_bar_count,
                "observed_complete_bar_count": observed_complete_bar_count,
                "missing_complete_bar_count": missing_complete_bar_count,
                "complete_bar_status": complete_bar_status,
                "zero_index_close_count": zero_index_close_count,
            }
            coverages.append(cov)

    coverages.sort(
        key=lambda x: (
            x["parent_article_id"],
            x["contract_id"],
            x["canonical_symbol"],
            x["metric"],
        )
    )
    return tuple(coverages)


def load_verified_w2_evidence(
    *,
    project_root: Path,
    candidate_root: Path,
    approved_design_path: Path,
    approved_design_sha: str,
    approved_plan_path: Path,
    approved_plan_sha: str,
    network_authorization_path: Path,
    network_authorization_sha: str,
) -> VerifiedW2Evidence:
    """Strictly loads and verifies candidate W2 historical price evidence package."""
    # 1. Directory and root path verification
    resolved_root = candidate_root.resolve()
    if not resolved_root.is_dir() or resolved_root.is_symlink():
        raise W2EvidenceSourceError(f"w2_root_invalid:candidate_root_not_dir:{candidate_root}")

    run_id = candidate_root.name
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id):
        raise W2EvidenceSourceError(f"w2_root_invalid:invalid_run_id:{run_id}")

    entries = sorted(list(candidate_root.iterdir()))
    for e in entries:
        if e.is_symlink():
            raise W2EvidenceSourceError(f"w2_root_invalid:symlink_detected:{e}")
        if e.name not in ("candidate_manifest.json", "zips", "csvs"):
            raise W2EvidenceSourceError(f"w2_root_invalid:unexpected_entry:{e.name}")

    manifest_path = candidate_root / "candidate_manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise W2EvidenceSourceError(f"w2_root_invalid:missing_manifest:{manifest_path}")

    # 2. Manifest top-level keys and schema version
    manifest_bytes = manifest_path.read_bytes()
    try:
        manifest_data = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as exc:
        raise W2EvidenceSourceError(f"w2_root_invalid:manifest_json_error:{exc}") from exc

    expected_keys = {
        "schema_version",
        "run_id",
        "authority_packet",
        "denominator_records",
        "logical_archive_records",
        "physical_source_objects",
        "metric_window_coverages",
        "request_set",
        "candidate_root_state",
        "capture_mode",
        "point_in_time_source_validated",
        "authority_flags",
    }
    if set(manifest_data.keys()) != expected_keys:
        raise W2EvidenceSourceError(f"w2_root_invalid:manifest_keys:{set(manifest_data.keys())}")

    if manifest_data["schema_version"] != W2_SCHEMA_VERSION:
        raise W2EvidenceSourceError(f"w2_root_invalid:schema_version:{manifest_data['schema_version']}")
    if manifest_data["run_id"] != run_id:
        raise W2EvidenceSourceError(f"w2_root_invalid:run_id_mismatch:{manifest_data['run_id']}!={run_id}")
    if manifest_data["capture_mode"] != "historical_ex_post_candidate":
        raise W2EvidenceSourceError(f"w2_root_invalid:capture_mode:{manifest_data['capture_mode']}")
    if manifest_data["point_in_time_source_validated"] is not False:
        raise W2EvidenceSourceError("w2_root_invalid:point_in_time_source_validated_must_be_false")

    # 3. Check authority flags (13 exact false flags)
    auth_flags = manifest_data["authority_flags"]
    if not isinstance(auth_flags, dict) or set(auth_flags.keys()) != set(W2_13_FALSE_FLAGS.keys()):
        raise W2EvidenceSourceError("w2_root_invalid:authority_flags_mismatch")
    for k, exp_val in W2_13_FALSE_FLAGS.items():
        if auth_flags.get(k) is not exp_val or type(auth_flags.get(k)) is not bool:
            raise W2EvidenceSourceError(f"w2_root_invalid:authority_flag_violation:{k}")

    # 4. Authority re-derivation
    coverage_matrix = project_root / "tests/fixtures/external_signal_shadow/stage1_6f/evidence_package/denominator_archive_coverage_matrix_all_intersecting.json"
    c_root = project_root / "data/external_signal_shadow/stage1_6a/sealed_export_source_audits/stage1_6a_audit_4d1c5092c5ce_20260913T072500Z"
    b_root = project_root / "data/external_signal_shadow/stage1_6b/historical_backfill/hist_20260913_072358_671ce365/sealed_exports/4d1c5092c5ce4c196c1055f61c728eb43a8eba8384ebed78f57487c6b664d090"
    canonical_002_root = project_root / "data/external_signal_shadow/stage1_6f/evidence_candidates/expansion_candidate_run_20260917_002"

    authority = derive_w2_authority_inputs(
        project_root=project_root,
        c_completed_root=c_root,
        b_source_export=b_root,
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

    # 5. Denominator records verification
    if manifest_data["denominator_records"] != list(authority.denominator_records):
        raise W2EvidenceSourceError("w2_root_invalid:denominator_records_mismatch")

    # 6. Physical source objects verification
    manifest_phys = manifest_data["physical_source_objects"]
    if len(manifest_phys) != len(request_set.physical_records):
        raise W2EvidenceSourceError(f"w2_root_invalid:physical_count_mismatch:{len(manifest_phys)}")

    loaded_csv_rows: dict[str, list[dict[str, Any]]] = {}
    phys_map: dict[str, dict[str, Any]] = {}

    for i, obj in enumerate(manifest_phys):
        exp_phys = request_set.physical_records[i]
        pid = obj.get("physical_source_object_id")
        if pid != exp_phys["physical_source_object_id"]:
            raise W2EvidenceSourceError(f"w2_root_invalid:physical_id_mismatch:{pid}!={exp_phys['physical_source_object_id']}")

        if obj.get("exact_source_url") != exp_phys["exact_source_url"]:
            raise W2EvidenceSourceError(f"w2_root_invalid:physical_url:{obj.get('exact_source_url')}!={exp_phys['exact_source_url']}")

        http_val = obj.get("http_status_or_transport_error")
        if isinstance(http_val, bool):
            raise W2EvidenceSourceError(f"w2_root_invalid:http_status_type:bool_not_permitted:{http_val}")

        acq = obj.get("acquisition_method")
        if acq == "copied_verified_002":
            if pid not in request_set.reuse_ids:
                raise W2EvidenceSourceError(f"w2_root_invalid:reuse_id_not_in_reuse_set:{pid}")
            if obj.get("network_attempt_count") != 0:
                raise W2EvidenceSourceError(f"w2_root_invalid:reuse_attempt_count_not_zero:{pid}")
            if http_val is not None:
                raise W2EvidenceSourceError(f"w2_root_invalid:http_status_type:reuse_http_must_be_null:{http_val}")
            if obj.get("fetch_status") != "fetched_verified":
                raise W2EvidenceSourceError(f"w2_root_invalid:reuse_status_must_be_verified:{obj.get('fetch_status')}")

            zip_rel = obj.get("zip_relative_path")
            csv_rel = obj.get("csv_relative_path")
            if not zip_rel or not csv_rel:
                raise W2EvidenceSourceError(f"w2_root_invalid:missing_zip_or_csv_path:{pid}")

            val_res = validate_w2_zip_and_csv(
                candidate_root / zip_rel,
                candidate_root / csv_rel,
                obj["exact_source_url"],
            )
            if val_res["zip_sha256"] != obj.get("zip_sha256") or val_res["zip_byte_length"] != obj.get("zip_byte_length"):
                raise W2EvidenceSourceError(f"w2_root_invalid:zip_hash_or_length_mismatch:{pid}")
            if val_res["csv_sha256"] != obj.get("csv_sha256") or val_res["csv_byte_length"] != obj.get("csv_byte_length"):
                raise W2EvidenceSourceError(f"w2_root_invalid:csv_hash_or_length_mismatch:{pid}")

            loaded_csv_rows[pid] = val_res["parsed_rows"]

        elif acq == "network_get":
            if pid not in request_set.fetch_ids:
                raise W2EvidenceSourceError(f"w2_root_invalid:fetch_id_not_in_fetch_set:{pid}")
            if obj.get("network_attempt_count") != 1:
                raise W2EvidenceSourceError(f"w2_root_invalid:fetch_attempt_count_not_one:{pid}")
            if http_val is not None and not isinstance(http_val, (int, str)):
                raise W2EvidenceSourceError(f"w2_root_invalid:http_status_type:{type(http_val)}")

            fetch_st = obj.get("fetch_status")
            zip_rel = obj.get("zip_relative_path")
            csv_rel = obj.get("csv_relative_path")

            if fetch_st == "fetched_verified":
                if http_val != 200:
                    raise W2EvidenceSourceError(f"w2_root_invalid:verified_http_not_200:{http_val}")
                if not zip_rel or not csv_rel:
                    raise W2EvidenceSourceError(f"w2_root_invalid:missing_zip_or_csv_path:{pid}")
                val_res = validate_w2_zip_and_csv(
                    candidate_root / zip_rel,
                    candidate_root / csv_rel,
                    obj["exact_source_url"],
                )
                if val_res["zip_sha256"] != obj.get("zip_sha256") or val_res["zip_byte_length"] != obj.get("zip_byte_length"):
                    raise W2EvidenceSourceError(f"w2_root_invalid:zip_hash_or_length_mismatch:{pid}")
                if val_res["csv_sha256"] != obj.get("csv_sha256") or val_res["csv_byte_length"] != obj.get("csv_byte_length"):
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_hash_or_length_mismatch:{pid}")
                if val_res["zip_member_name"] != obj.get("zip_member_name"):
                    raise W2EvidenceSourceError(f"w2_root_invalid:zip_member_name_mismatch:{pid}")
                if val_res["csv_header"] != obj.get("csv_header"):
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_header_mismatch:{pid}")
                if val_res["csv_row_count"] != obj.get("csv_row_count"):
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_row_count_mismatch:{pid}")
                if val_res["first_row"] != obj.get("first_row") or val_res["last_row"] != obj.get("last_row"):
                    raise W2EvidenceSourceError(f"w2_root_invalid:first_or_last_row_mismatch:{pid}")
                loaded_csv_rows[pid] = val_res["parsed_rows"]

            elif fetch_st == "archive_invalid":
                if http_val != 200:
                    raise W2EvidenceSourceError(f"w2_root_invalid:archive_invalid_http_must_be_200:{http_val}")
                if zip_rel != f"zips/{pid}.zip":
                    raise W2EvidenceSourceError(f"w2_root_invalid:archive_invalid_zip_path:{zip_rel}")
                zip_p = candidate_root / zip_rel
                if not zip_p.is_file() or zip_p.is_symlink():
                    raise W2EvidenceSourceError(f"w2_root_invalid:archive_invalid_zip_missing:{zip_p}")
                z_hasher = hashlib.sha256()
                z_len = 0
                with open(zip_p, "rb") as zf:
                    while True:
                        ch = zf.read(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES)
                        if not ch:
                            break
                        z_hasher.update(ch)
                        z_len += len(ch)
                if z_len != obj.get("zip_byte_length") or z_len > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES:
                    raise W2EvidenceSourceError(f"w2_root_invalid:archive_invalid_zip_len_mismatch:{z_len}")
                if z_hasher.hexdigest() != obj.get("zip_sha256"):
                    raise W2EvidenceSourceError("w2_root_invalid:archive_invalid_zip_sha_mismatch")
                if csv_rel is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:archive_invalid_csv_path_must_be_null:{pid}")
                if (candidate_root / f"csvs/{pid}.csv").exists():
                    raise W2EvidenceSourceError(f"w2_root_invalid:archive_invalid_csv_file_must_not_exist:{pid}")
                if obj.get("csv_byte_length") is not None or obj.get("csv_sha256") is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:archive_invalid_csv_metadata_must_be_null:{pid}")
                if obj.get("csv_row_count") != 0 or obj.get("first_row") is not None or obj.get("last_row") is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:archive_invalid_csv_rows_must_be_zero_and_null:{pid}")

            elif fetch_st == "csv_invalid":
                if http_val != 200:
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_invalid_http_must_be_200:{http_val}")
                if zip_rel != f"zips/{pid}.zip" or csv_rel != f"csvs/{pid}.csv":
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_invalid_paths_mismatch:{pid}")
                zip_p = candidate_root / zip_rel
                csv_p = candidate_root / csv_rel
                if not zip_p.is_file() or zip_p.is_symlink():
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_invalid_zip_missing:{zip_p}")
                if not csv_p.is_file() or csv_p.is_symlink():
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_invalid_csv_missing:{csv_p}")
                z_hasher = hashlib.sha256()
                z_len = 0
                with open(zip_p, "rb") as zf:
                    while True:
                        ch = zf.read(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES)
                        if not ch:
                            break
                        z_hasher.update(ch)
                        z_len += len(ch)
                if z_len != obj.get("zip_byte_length") or z_len > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_ZIP_BYTES:
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_invalid_zip_len_mismatch:{z_len}")
                if z_hasher.hexdigest() != obj.get("zip_sha256"):
                    raise W2EvidenceSourceError("w2_root_invalid:csv_invalid_zip_sha_mismatch")
                c_hasher = hashlib.sha256()
                c_len = 0
                with open(csv_p, "rb") as cf:
                    while True:
                        ch = cf.read(EXTERNAL_SIGNAL_STAGE1_6F_W2_CHUNK_BYTES)
                        if not ch:
                            break
                        c_hasher.update(ch)
                        c_len += len(ch)
                if c_len != obj.get("csv_byte_length") or c_len > EXTERNAL_SIGNAL_STAGE1_6F_W2_MAX_CSV_BYTES:
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_invalid_csv_len_mismatch:{c_len}")
                if c_hasher.hexdigest() != obj.get("csv_sha256"):
                    raise W2EvidenceSourceError("w2_root_invalid:csv_invalid_csv_sha_mismatch")
                expected_zip_basename = exp_phys["exact_source_url"].split("/")[-1]
                expected_csv_member = expected_zip_basename[:-4] + ".csv" if expected_zip_basename.endswith(".zip") else expected_zip_basename
                if obj.get("zip_member_name") != expected_csv_member:
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_invalid_member_mismatch:{obj.get('zip_member_name')}")
                if obj.get("csv_row_count") != 0 or obj.get("first_row") is not None or obj.get("last_row") is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:csv_invalid_row_count_must_be_zero:{pid}")

            elif fetch_st == "archive_not_found_404":
                if http_val != 404:
                    raise W2EvidenceSourceError(f"w2_root_invalid:404_http_must_be_404:{http_val}")
                if zip_rel is not None or csv_rel is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:404_must_have_null_paths:{pid}")
                if obj.get("csv_row_count") != 0 or obj.get("first_row") is not None or obj.get("last_row") is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:404_must_have_null_rows:{pid}")
                if (candidate_root / f"zips/{pid}.zip").exists() or (candidate_root / f"csvs/{pid}.csv").exists():
                    raise W2EvidenceSourceError(f"w2_root_invalid:404_files_must_not_exist:{pid}")

            elif fetch_st == "redirect_refused":
                if not (isinstance(http_val, int) and 300 <= http_val < 400):
                    raise W2EvidenceSourceError(f"w2_root_invalid:redirect_code:{http_val}")
                if zip_rel is not None or csv_rel is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:redirect_must_have_null_paths:{pid}")
                if obj.get("csv_row_count") != 0 or obj.get("first_row") is not None or obj.get("last_row") is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:redirect_must_have_null_rows:{pid}")
                if (candidate_root / f"zips/{pid}.zip").exists() or (candidate_root / f"csvs/{pid}.csv").exists():
                    raise W2EvidenceSourceError(f"w2_root_invalid:redirect_files_must_not_exist:{pid}")

            elif fetch_st == "transport_inconclusive":
                if zip_rel is not None or csv_rel is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:transport_must_have_null_paths:{pid}")
                if obj.get("csv_row_count") != 0 or obj.get("first_row") is not None or obj.get("last_row") is not None:
                    raise W2EvidenceSourceError(f"w2_root_invalid:transport_must_have_null_rows:{pid}")
                if (candidate_root / f"zips/{pid}.zip").exists() or (candidate_root / f"csvs/{pid}.csv").exists():
                    raise W2EvidenceSourceError(f"w2_root_invalid:transport_files_must_not_exist:{pid}")
            else:
                raise W2EvidenceSourceError(f"w2_root_invalid:unknown_fetch_status:{fetch_st}")
        else:
            raise W2EvidenceSourceError(f"w2_root_invalid:unknown_acquisition_method:{acq}")

        phys_map[pid] = obj

    expected_zips = {
        obj["zip_relative_path"].split("/")[-1]
        for obj in manifest_phys if obj.get("zip_relative_path") is not None
    }
    expected_csvs = {
        obj["csv_relative_path"].split("/")[-1]
        for obj in manifest_phys if obj.get("csv_relative_path") is not None
    }
    actual_zips = {p.name for p in (candidate_root / "zips").iterdir() if not p.is_symlink()}
    actual_csvs = {p.name for p in (candidate_root / "csvs").iterdir() if not p.is_symlink()}
    if actual_zips != expected_zips:
        raise W2EvidenceSourceError(f"w2_root_invalid:zips_directory_files_mismatch:{actual_zips ^ expected_zips}")
    if actual_csvs != expected_csvs:
        raise W2EvidenceSourceError(f"w2_root_invalid:csvs_directory_files_mismatch:{actual_csvs ^ expected_csvs}")

    # 7. Logical records verification
    manifest_log = manifest_data["logical_archive_records"]
    if len(manifest_log) != len(request_set.logical_records):
        raise W2EvidenceSourceError(f"w2_root_invalid:logical_count_mismatch:{len(manifest_log)}")

    for i, log_rec in enumerate(manifest_log):
        exp_log = request_set.logical_records[i]
        if log_rec["logical_archive_record_id"] != exp_log["logical_archive_record_id"]:
            raise W2EvidenceSourceError(f"w2_root_invalid:logical_id_mismatch:{log_rec['logical_archive_record_id']}")
        pid = log_rec["physical_source_object_id"]
        if pid != exp_log["physical_source_object_id"]:
            raise W2EvidenceSourceError(f"w2_root_invalid:logical_physical_id_mismatch:{pid}")
        if log_rec["record_state"] != phys_map[pid]["fetch_status"]:
            raise W2EvidenceSourceError(f"w2_root_invalid:logical_record_state_mismatch:{log_rec['record_state']}")

    # 8. Recompute metric window coverages and compare
    recomputed_coverages = compute_w2_metric_coverages(
        authority.denominator_records,
        manifest_log,
        phys_map,
        loaded_csv_rows,
    )
    if manifest_data["metric_window_coverages"] != list(recomputed_coverages):
        raise W2EvidenceSourceError("w2_root_invalid:metric_window_coverages_mismatch")

    # 9. Candidate root state verification
    root_state = manifest_data["candidate_root_state"]
    if root_state == "collection_terminal_all_complete_bars":
        # Check if all 123 are observed
        all_observed = all(c["complete_bar_status"] == "observed" for c in recomputed_coverages)
        if not all_observed:
            raise W2EvidenceSourceError("w2_root_invalid:candidate_root_state:cannot_be_all_complete_with_gaps")
    elif root_state != "collection_terminal_with_evidence_gaps":
        raise W2EvidenceSourceError(f"w2_root_invalid:candidate_root_state:{root_state}")

    return VerifiedW2Evidence(
        run_id=run_id,
        completed_root=candidate_root,
        manifest=manifest_data,
        denominator_records=authority.denominator_records,
        logical_archive_records=tuple(manifest_log),
        physical_source_objects=tuple(manifest_phys),
        metric_window_coverages=recomputed_coverages,
        candidate_root_state=root_state,
    )

