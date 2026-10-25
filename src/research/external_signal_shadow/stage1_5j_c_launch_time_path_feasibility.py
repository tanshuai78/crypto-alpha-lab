"""Stage 1.5J-C Launch Time and Path Feasibility Diagnostic Core Module.

Implements:
1. Fixed protocol verification and frozen upstream authority checks.
2. Custodian release and 11-line approval verification -> derived run_authorization.json.
3. Read-only ledger 281-key bijection and J-A article AST coordinate verification.
4. J-C package admission and local bounded streaming reader (<= 65,536 bytes per read).
5. Exact rational (Fraction) child trajectory reduction, first-passage detection, and EOF streaming.
"""

from __future__ import annotations

import contextlib
import csv
import fcntl
import hashlib
import io
import json
import math
import os
import re
import zipfile
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any

from configs.base import RISK_LIVE_TRADING_ENABLED
from configs.stage1_5j_b_historical_aggtrades_launch_response import (
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
)
from research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
    load_verified_stage1_5j_a_historical_archive_coverage_root,
)
from research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
    load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
    validate_zip_archive_package,
)


class Stage1_5JCDiagnosticError(Exception):
    """Base fail-closed diagnostic error for Stage 1.5J-C."""


class Stage1_5JCPostRenameDurabilityFailure(Stage1_5JCDiagnosticError):
    """Raised when parent directory fsync fails after atomic rename."""


PROFILE_ID = "stage1_5j_c_time_path_v1"
PROFILE_CONTRACT_VERSION = 1

APPROVED_DESIGN_RELATIVE_PATH = (
    "docs/designs/2026-10-23-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-design_CN.md"
)
APPROVED_DESIGN_SHA256 = "32d5130806489c0848748060835a7c0fb8f1715a3f9fb6b479c2f02cff5d4e45"

APPROVED_PLAN_RELATIVE_PATH = (
    "docs/plans/2026-10-24-external-signal-shadow-lab-stage1-5j-c-launch-time-path-feasibility-implementation-plan-r1_CN.md"
)

PROTOCOL_RELATIVE_PATH = "docs/production_artifacts/stage1_5j_c_time_path_protocol_v1.json"
PROTOCOL_SHA256 = "4dd353751256191d75fc52388413d97e5a7b177e499bbee28e2dd2ff356e1cbe"
EXPECTED_PROTOCOL_OBJECT: dict[str, Any] = {
    "endpoint_max_age_ms": 1000,
    "entry_max_wait_ms": 1000,
    "friction_bps": [50, 80, 150],
    "horizon_ms": 900000,
    "latency_ms": 3000,
    "observation_ms": 60000,
    "protocol_id": "stage1_5j_c_time_path_v1",
    "protocol_version": 1,
    "risk_bps": 200,
    "target_bps": 3000,
}

J_A_ROOT_RELATIVE_PATH = (
    "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/"
    "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
)
J_A_RUN_ID = "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"

J_B_ROOT_RELATIVE_PATH = (
    "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/"
    "stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"
)
J_B_RUN_ID = "stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"

LEDGER_RELATIVE_PATH = "data/exports/stage1_5j_token_launch_classification_ledger_v2.csv"
LEDGER_SHA256 = "36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b"

J_B_CLOSURE_JSON_RELATIVE_PATH = (
    ".git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/"
    "64e14726202b53727a7627139578369cb6af54f08d5a785d4df006009eb25a2d/"
    "evidence/receipt_closure_evidence.json"
)
J_B_CLOSURE_JSON_SHA256 = "8d535303d61b3860eaa69018eff3f76645f91b3e27af1af89e1e956b948f8b6d"
J_B_CLOSURE_SIDECAR_RELATIVE_PATH = f"{J_B_CLOSURE_JSON_RELATIVE_PATH}.sha256"
J_B_CLOSURE_SIDECAR_SHA256 = "c3856c2e9e6d5086a543891902d57246fa64a93acdbba97a1130e541f949c5d9"

FROZEN_SOURCE_FILE_HASHES: dict[str, str] = {
    "configs/base.py": "473dd4e9c997524ab064e79b470ff41f0ac7e2e42013457891e4e83e4a7b13bc",
    "configs/stage1_5j_b_historical_aggtrades_launch_response.py": "771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4",
    "scripts/external_signal_shadow/export_stage1_5j_dataset_v2.py": "b70faa18f4da875d1c3db950b312d97f49551b4887f22c2baf3b96531e6926d8",
    "scripts/external_signal_shadow/verify_stage1_5j_dataset_v2.py": "52623af3d766ad52e45b0ca61dd748340cd664644f855b800f5cd7ffc28fb3ee",
    "scripts/governance/verify_artifact_schema.py": "7e621e1c015c0c9d49d5430209f085ce088a046ea66bf259961349566e6fd473",
    "scripts/governance/verify_stage1_5j_b_receipt_schema.py": "442c527fb7f49d78eff4e13fd68e5fabfff12ba1e74089cd5e5133977cde90f1",
    "src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py": "250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18",
    "src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py": "b2ca8e286d4737c79a5d5bf881e797f041cdea1e2837c64401d04123eb02fa4f",
}

J_C_SOURCE_RELATIVE_PATHS: tuple[str, ...] = (
    "scripts/external_signal_shadow/run_stage1_5j_c_launch_time_path_feasibility.py",
    "scripts/governance/verify_stage1_5j_c_receipt_schema.py",
    "src/research/external_signal_shadow/stage1_5j_c_launch_time_path_feasibility.py",
)

ALL_11_SOURCE_RELATIVE_PATHS: tuple[str, ...] = tuple(
    sorted(list(FROZEN_SOURCE_FILE_HASHES.keys()) + list(J_C_SOURCE_RELATIVE_PATHS))
)

FROZEN_INPUT_FILE_HASHES: dict[str, str] = {
    J_B_CLOSURE_JSON_RELATIVE_PATH: J_B_CLOSURE_JSON_SHA256,
    J_B_CLOSURE_SIDECAR_RELATIVE_PATH: J_B_CLOSURE_SIDECAR_SHA256,
    LEDGER_RELATIVE_PATH: LEDGER_SHA256,
    f"{J_A_ROOT_RELATIVE_PATH}/manifest.json": "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf",
    f"{J_A_ROOT_RELATIVE_PATH}/summary.json": "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b",
    f"{J_B_ROOT_RELATIVE_PATH}/manifest.json": "f0a8ac724925084161f6b9aa2dced5139b261707fda0f0f21ebd0eb6de3087fb",
    f"{J_B_ROOT_RELATIVE_PATH}/review_CN.md": "17e9ffaa973923868621a8ee925dc811c15e12459924ee63897f9c21fcac317e",
    f"{J_B_ROOT_RELATIVE_PATH}/summary.json": "5ea0f1c87803114c4c6917cd0c3d24292948fa0e7066a80e0a2bce611e32546b",
    PROTOCOL_RELATIVE_PATH: PROTOCOL_SHA256,
}

ALL_9_INPUT_RELATIVE_PATHS: tuple[str, ...] = tuple(sorted(FROZEN_INPUT_FILE_HASHES.keys()))

OUTPUT_PARENT_RELATIVE_PATH = (
    "data/external_signal_shadow/stage1_5j_c/launch_time_path_feasibility"
)
RUN_ID_REGEX = re.compile(
    r"^stage1_5j_c_launch_time_path_feasibility_([0-9]{8}T[0-9]{6}Z)$"
)
SHA256_REGEX = re.compile(r"^[0-9a-f]{64}$")
HEX32_REGEX = re.compile(r"^[0-9a-f]{32}$")
DATE_REGEX = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
FRACTION_REGEX = re.compile(r"^(?:0/1|-?[1-9][0-9]*/[1-9][0-9]*)$")
NONNEG_INT_STR_REGEX = re.compile(r"^(?:0|[1-9][0-9]*)$")

REQUIRED_CSV_HEADER = [
    "agg_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time",
    "is_buyer_maker",
]

REQUIRED_LEDGER_COLUMNS = [
    "parent_article_id",
    "symbol",
    "asset_class",
    "listing_regime",
    "classification_status",
    "table_index",
    "symbol_column_index",
    "field_header",
    "raw_cell_value",
    "evidence_locator",
    "source_relative_path",
    "source_sha256",
]

ALLOWED_ASSET_CLASSES = {"crypto", "equity", "etf", "commodity", "index", "unknown"}
ALLOWED_LISTING_REGIMES = {"standard", "pre_market", "pre_ipo", "unknown"}
ALLOWED_CLASSIFICATION_STATUS = {"confirmed", "unknown"}
ALLOWED_OPERATIONS = {
    "offline_time_path_validation_once": "validation_only",
    "offline_time_path_diagnostic_once": "production_diagnostic",
}

APPROVAL_ORDERED_KEYS = (
    "APPROVED_J_C_PLAN_RELATIVE_PATH",
    "APPROVED_J_C_PLAN_SHA256",
    "AUTHORIZED_SOURCE_BUNDLE_SHA256",
    "AUTHORIZED_OPERATION",
    "AUTHORIZED_RUN_ID",
    "AUTHORIZED_OUTPUT_ROOT",
    "NETWORK_ALLOWED",
    "SIGNAL_ALLOWED",
    "PAPER_TRADING_ALLOWED",
    "LIVE_TRADING_ALLOWED",
    "EXECUTION_ALLOWED",
)

RELEASE_EXACT_KEYS = {
    "release_schema_version",
    "release_state",
    "user_receipt_generation_approval",
    "design",
    "plan",
    "authorized_source_bundle_sha256",
    "operation",
    "run_id",
    "output_root",
    "network_allowed",
    "signal_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_allowed",
}

DERIVED_AUTH_EXACT_KEYS = {
    "design",
    "plan",
    "user_receipt_generation_approval",
    "authorization_release",
    "authorized_source_bundle_sha256",
    "run_id",
    "output_root",
    "source_files",
    "input_files",
    "operation",
    "network_allowed",
    "signal_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_allowed",
}

CANONICAL_PERMISSIONS: dict[str, bool] = {
    "alpha_claim_allowed": False,
    "consumer_promotion_allowed": False,
    "execution_allowed": False,
    "live_trading_allowed": False,
    "network_allowed": False,
    "paper_trading_allowed": False,
    "receipt_regeneration_allowed": False,
    "signal_allowed": False,
}


def resolve_project_root() -> Path:
    """Resolve repository root directory."""
    return Path(__file__).resolve().parents[3]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES):
            h.update(chunk)
    return h.hexdigest()


def _has_symlink_ancestor(path: Path, stop_at: Path | None = None) -> bool:
    cur = path
    stop_resolved = stop_at.resolve() if stop_at is not None and stop_at.exists() else None
    while True:
        if os.path.islink(cur):
            return True
        if stop_resolved is not None and cur.exists():
            try:
                if cur.resolve() == stop_resolved:
                    break
            except OSError:
                return True
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return False


def _dump_canonical_json_bytes(obj: Any) -> bytes:
    text = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def _parse_canonical_json_bytes(raw: bytes, context: str) -> Any:
    if not raw.endswith(b"\n") or raw.endswith(b"\r\n") or raw.startswith(b"\xef\xbb\xbf"):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:noncanonical_json_newline_or_bom:{context}"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:utf8_decode_failed:{context}"
        ) from exc

    def _no_dup_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        seen: set[str] = set()
        out: dict[str, Any] = {}
        for k, v in pairs:
            if k in seen:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_authority_mismatch:duplicate_json_key:{context}:{k}"
                )
            seen.add(k)
            out[k] = v
        return out

    def _reject_const(val: str) -> Any:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:nan_or_inf_forbidden:{context}:{val}"
        )

    try:
        parsed = json.loads(
            text[:-1],
            object_pairs_hook=_no_dup_pairs,
            parse_constant=_reject_const,
        )
    except Stage1_5JCDiagnosticError:
        raise
    except Exception as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:json_parse_error:{context}:{exc}"
        ) from exc

    expected_bytes = _dump_canonical_json_bytes(parsed)
    if raw != expected_bytes:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:noncanonical_json_bytes:{context}"
        )
    return parsed


def load_and_verify_protocol(protocol_path: Path | None = None) -> dict[str, Any]:
    """Load and verify the sole fixed Stage 1.5J-C measurement protocol JSON."""
    p = (
        protocol_path
        if protocol_path is not None
        else (resolve_project_root() / PROTOCOL_RELATIVE_PATH)
    )
    if os.path.islink(p) or not p.is_file():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:protocol_missing_or_symlink:{p}"
        )
    raw = p.read_bytes()
    parsed = _parse_canonical_json_bytes(raw, "protocol")
    if not isinstance(parsed, dict) or set(parsed.keys()) != set(EXPECTED_PROTOCOL_OBJECT.keys()):
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_authority_mismatch:protocol_keyset_mismatch"
        )
    if _sha256_bytes(raw) != PROTOCOL_SHA256 or parsed != EXPECTED_PROTOCOL_OBJECT:
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_authority_mismatch:protocol_value_or_sha_mismatch"
        )
    for k, exp_v in EXPECTED_PROTOCOL_OBJECT.items():
        obs_v = parsed[k]
        if isinstance(exp_v, list):
            if (
                not isinstance(obs_v, list)
                or len(obs_v) != len(exp_v)
                or any(type(x) is not int for x in obs_v)
            ):
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_authority_mismatch:protocol_field_type:{k}"
                )
        elif isinstance(exp_v, int):
            if type(obs_v) is not int:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_authority_mismatch:protocol_field_type:{k}"
                )
        elif isinstance(exp_v, str):
            if type(obs_v) is not str:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_authority_mismatch:protocol_field_type:{k}"
                )
    return parsed


def format_exact_fraction(value: Fraction) -> str:
    """Serialize an exact Fraction to reduced 'numerator/denominator' string ('0/1' for zero)."""
    if not isinstance(value, Fraction):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_fraction_invalid:not_a_fraction:{type(value)}"
        )
    if value.numerator == 0:
        return "0/1"
    return f"{value.numerator}/{value.denominator}"


def parse_exact_fraction(text: str) -> Fraction:
    """Parse canonical reduced 'numerator/denominator' string into Fraction."""
    if not isinstance(text, str) or not FRACTION_REGEX.match(text):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_fraction_invalid:syntax:{text!r}"
        )
    num_s, den_s = text.split("/", 1)
    num = int(num_s)
    den = int(den_s)
    if den <= 0 or math.gcd(abs(num), den) != 1:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_fraction_invalid:unreduced:{text!r}"
        )
    return Fraction(num, den)


def format_display_decimal_from_fraction(value: Fraction) -> str:
    """Format a Fraction to 8 decimal places using ROUND_HALF_EVEN for human display only."""
    d_num = Decimal(value.numerator)
    d_den = Decimal(value.denominator)
    q = (d_num / d_den).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
    return format(q, "f")


def compute_required_utc_dates(t0_ms: int, horizon_ms: int = 900000) -> list[str]:
    """Return sorted list of YYYY-MM-DD UTC dates intersecting [t0_ms, t0_ms + horizon_ms]."""
    if type(t0_ms) is not int or type(horizon_ms) is not int or t0_ms <= 0 or horizon_ms < 0:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_time_window_invalid:{t0_ms}:{horizon_ms}"
        )
    start_dt = datetime.fromtimestamp(t0_ms // 1000, tz=timezone.utc).date()
    end_dt = datetime.fromtimestamp((t0_ms + horizon_ms) // 1000, tz=timezone.utc).date()
    dates: list[str] = []
    cur = start_dt
    while cur <= end_dt:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return dates


def _utc_date_bounds_ms(utc_date: str) -> tuple[int, int]:
    if not isinstance(utc_date, str) or not DATE_REGEX.match(utc_date):
        raise Stage1_5JCDiagnosticError(f"STOP=stage1_5j_c_utc_date_invalid:{utc_date!r}")
    try:
        dt = datetime.strptime(utc_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_utc_date_invalid:{utc_date!r}"
        ) from exc
    start_ms = int(dt.timestamp() * 1000)
    end_ms = start_ms + 86_400_000
    return start_ms, end_ms


def _parse_positive_finite_decimal_str(raw_str: str, field_name: str) -> Decimal:
    if (
        not isinstance(raw_str, str)
        or not raw_str
        or raw_str != raw_str.strip()
        or raw_str.startswith("+")
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_csv_numeric_invalid:{field_name}:{raw_str!r}"
        )
    try:
        d = Decimal(raw_str)
    except InvalidOperation as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_csv_numeric_invalid:{field_name}:{raw_str!r}"
        ) from exc
    if not d.is_finite() or d <= Decimal(0):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_csv_numeric_invalid:{field_name}:{raw_str!r}"
        )
    return d


def _parse_nonneg_int_str(raw_str: str, field_name: str) -> int:
    if not isinstance(raw_str, str) or not NONNEG_INT_STR_REGEX.match(raw_str):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_csv_numeric_invalid:{field_name}:{raw_str!r}"
        )
    return int(raw_str)


def _make_trade_ref(
    utc_date: str,
    physical_row: int,
    agg_trade_id: int,
    time_ms: int,
    price_str: str,
) -> dict[str, Any]:
    return {
        "agg_trade_id": agg_trade_id,
        "physical_row": physical_row,
        "price": price_str,
        "time_ms": time_ms,
        "utc_date": utc_date,
    }


def _make_gap_child_pair(
    parent_article_id: str,
    symbol: str,
    listing_regime: str,
    state: str,
    t0_ref: dict[str, Any] | None = None,
    entry_ref: dict[str, Any] | None = None,
    endpoint_ref: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for direction in ("long", "short"):
        rows.append(
            {
                "direction": direction,
                "endpoint": dict(endpoint_ref) if endpoint_ref is not None else None,
                "entry": dict(entry_ref) if entry_ref is not None else None,
                "first_touch": "unavailable",
                "listing_regime": listing_regime,
                "mae_bps": None,
                "mae_trade": None,
                "max_intertrade_gap_ms": None,
                "mfe_bps": None,
                "mfe_trade": None,
                "parent_article_id": parent_article_id,
                "state": state,
                "symbol": symbol,
                "t0": dict(t0_ref) if t0_ref is not None else None,
                "terminal_bps": None,
                "touch_trade": None,
            }
        )
    return rows


def reduce_child_time_path_from_trades(
    parent_article_id: str,
    symbol: str,
    listing_regime: str,
    symbol_launch_time_ms: int,
    expected_anchor_time_ms: int,
    expected_anchor_price: str,
    trades: Iterable[dict[str, Any]],
    protocol: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Reduce a validated trade iterator into two directional J-C Child rows (long, short)."""
    proto = protocol if protocol is not None else EXPECTED_PROTOCOL_OBJECT
    obs_ms = int(proto["observation_ms"])
    lat_ms = int(proto["latency_ms"])
    entry_wait_ms = int(proto["entry_max_wait_ms"])
    horizon_ms = int(proto["horizon_ms"])
    endpoint_age_ms = int(proto["endpoint_max_age_ms"])
    target_bps_frac = Fraction(int(proto["target_bps"]), 1)
    risk_bps_frac = Fraction(-int(proto["risk_bps"]), 1)
    bps_scale = Fraction(10000, 1)
    one_frac = Fraction(1, 1)

    expected_anchor_dec = _parse_positive_finite_decimal_str(
        expected_anchor_price, "expected_anchor_price"
    )

    t0_ref: dict[str, Any] | None = None
    t_decision: int = 0
    entry_end: int = 0
    t_end: int = 0
    endpoint_start: int = 0

    entry_ref: dict[str, Any] | None = None
    entry_price_frac: Fraction | None = None
    endpoint_ref: dict[str, Any] | None = None

    prev_tid_global: int | None = None
    prev_ts_global: int | None = None

    prev_tid_since_t0: int | None = None
    gap_since_t0 = False
    sequence_gap_at_endpoint = False

    long_mfe = Fraction(0, 1)
    long_mfe_trade: dict[str, Any] | None = None
    long_mae = Fraction(0, 1)
    long_mae_trade: dict[str, Any] | None = None
    long_first_touch = "neither"
    long_touch_trade: dict[str, Any] | None = None

    short_mfe = Fraction(0, 1)
    short_mfe_trade: dict[str, Any] | None = None
    short_mae = Fraction(0, 1)
    short_mae_trade: dict[str, Any] | None = None
    short_first_touch = "neither"
    short_touch_trade: dict[str, Any] | None = None

    max_intertrade_gap_ms = 0
    prev_path_time_ms: int | None = None
    last_endpoint_long_bps = Fraction(0, 1)
    last_endpoint_short_bps = Fraction(0, 1)

    for tr in trades:
        utc_date = str(tr["utc_date"])
        phys_row = int(tr["physical_row"])
        tid = int(tr["agg_trade_id"])
        price_str = str(tr["price"])
        qty_str = str(tr["quantity"])
        fid = int(tr["first_trade_id"])
        lid = int(tr["last_trade_id"])
        ts = int(tr["transact_time"])
        bm_str = str(tr["is_buyer_maker"])

        if phys_row <= 0 or tid < 0 or fid < 0 or lid < 0 or ts < 0 or fid > lid:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_csv_trade_ids_invalid:{symbol}:{phys_row}"
            )
        if bm_str not in ("true", "false", "True", "False"):
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_csv_boolean_invalid:{symbol}:{bm_str!r}"
            )
        day_start, day_end = _utc_date_bounds_ms(utc_date)
        if not (day_start <= ts < day_end):
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_csv_date_bounds_invalid:{symbol}:{utc_date}:{ts}"
            )

        p_dec = _parse_positive_finite_decimal_str(price_str, "price")
        _parse_positive_finite_decimal_str(qty_str, "quantity")

        if prev_tid_global is not None and tid <= prev_tid_global:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_csv_agg_trade_id_order_invalid:{symbol}:{tid}<={prev_tid_global}"
            )
        if prev_ts_global is not None and ts < prev_ts_global:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_csv_timestamp_order_invalid:{symbol}:{ts}<{prev_ts_global}"
            )
        prev_tid_global = tid
        prev_ts_global = ts

        if t0_ref is None:
            if ts >= symbol_launch_time_ms:
                delay = ts - symbol_launch_time_ms
                if (
                    delay > EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS
                    or ts != expected_anchor_time_ms
                    or p_dec != expected_anchor_dec
                ):
                    raise Stage1_5JCDiagnosticError(
                        f"STOP=stage1_5j_c_anchor_replay_mismatch:{symbol}:{ts}:{price_str}"
                    )
                t0_ref = _make_trade_ref(utc_date, phys_row, tid, ts, price_str)
                t_decision = ts + obs_ms + lat_ms
                entry_end = t_decision + entry_wait_ms
                t_end = ts + horizon_ms
                endpoint_start = t_end - endpoint_age_ms
                prev_tid_since_t0 = tid
            continue

        # Already past T0: keep streaming to EOF for integrity, only reduce within <= t_end
        if ts <= t_end:
            assert prev_tid_since_t0 is not None
            if tid != prev_tid_since_t0 + 1:
                gap_since_t0 = True
            prev_tid_since_t0 = tid

            cur_ref = _make_trade_ref(utc_date, phys_row, tid, ts, price_str)
            p_frac = Fraction(p_dec)

            if entry_ref is None:
                if t_decision <= ts <= entry_end:
                    entry_ref = cur_ref
                    entry_price_frac = p_frac
                    long_mfe = Fraction(0, 1)
                    long_mfe_trade = cur_ref
                    long_mae = Fraction(0, 1)
                    long_mae_trade = cur_ref
                    short_mfe = Fraction(0, 1)
                    short_mfe_trade = cur_ref
                    short_mae = Fraction(0, 1)
                    short_mae_trade = cur_ref
                    prev_path_time_ms = ts
                    max_intertrade_gap_ms = 0
                    if endpoint_start <= ts <= t_end:
                        endpoint_ref = cur_ref
                        sequence_gap_at_endpoint = gap_since_t0
                        last_endpoint_long_bps = Fraction(0, 1)
                        last_endpoint_short_bps = Fraction(0, 1)
            else:
                assert entry_price_frac is not None
                assert prev_path_time_ms is not None
                dt_gap = ts - prev_path_time_ms
                if dt_gap > max_intertrade_gap_ms:
                    max_intertrade_gap_ms = dt_gap
                prev_path_time_ms = ts

                long_bps = bps_scale * (p_frac / entry_price_frac - one_frac)
                short_bps = bps_scale * (one_frac - p_frac / entry_price_frac)

                if long_bps > long_mfe:
                    long_mfe = long_bps
                    long_mfe_trade = cur_ref
                if long_bps < long_mae:
                    long_mae = long_bps
                    long_mae_trade = cur_ref

                if short_bps > short_mfe:
                    short_mfe = short_bps
                    short_mfe_trade = cur_ref
                if short_bps < short_mae:
                    short_mae = short_bps
                    short_mae_trade = cur_ref

                if long_first_touch == "neither":
                    if long_bps >= target_bps_frac:
                        long_first_touch = "target"
                        long_touch_trade = cur_ref
                    elif long_bps <= risk_bps_frac:
                        long_first_touch = "risk"
                        long_touch_trade = cur_ref

                if short_first_touch == "neither":
                    if short_bps >= target_bps_frac:
                        short_first_touch = "target"
                        short_touch_trade = cur_ref
                    elif short_bps <= risk_bps_frac:
                        short_first_touch = "risk"
                        short_touch_trade = cur_ref

                if endpoint_start <= ts <= t_end:
                    endpoint_ref = cur_ref
                    sequence_gap_at_endpoint = gap_since_t0
                    last_endpoint_long_bps = long_bps
                    last_endpoint_short_bps = short_bps

    if t0_ref is None:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_anchor_replay_missing:{parent_article_id}:{symbol}"
        )

    if entry_ref is None:
        return _make_gap_child_pair(
            parent_article_id,
            symbol,
            listing_regime,
            "entry_unavailable",
            t0_ref=t0_ref,
        )

    if endpoint_ref is None:
        return _make_gap_child_pair(
            parent_article_id,
            symbol,
            listing_regime,
            "endpoint_unavailable",
            t0_ref=t0_ref,
            entry_ref=entry_ref,
        )

    if sequence_gap_at_endpoint:
        return _make_gap_child_pair(
            parent_article_id,
            symbol,
            listing_regime,
            "sequence_gap",
            t0_ref=t0_ref,
            entry_ref=entry_ref,
            endpoint_ref=endpoint_ref,
        )

    assert long_mfe_trade is not None and long_mae_trade is not None
    assert short_mfe_trade is not None and short_mae_trade is not None

    long_row: dict[str, Any] = {
        "direction": "long",
        "endpoint": dict(endpoint_ref),
        "entry": dict(entry_ref),
        "first_touch": long_first_touch,
        "listing_regime": listing_regime,
        "mae_bps": format_exact_fraction(long_mae),
        "mae_trade": dict(long_mae_trade),
        "max_intertrade_gap_ms": max_intertrade_gap_ms,
        "mfe_bps": format_exact_fraction(long_mfe),
        "mfe_trade": dict(long_mfe_trade),
        "parent_article_id": parent_article_id,
        "state": "complete",
        "symbol": symbol,
        "t0": dict(t0_ref),
        "terminal_bps": format_exact_fraction(last_endpoint_long_bps),
        "touch_trade": dict(long_touch_trade) if long_touch_trade is not None else None,
    }
    short_row: dict[str, Any] = {
        "direction": "short",
        "endpoint": dict(endpoint_ref),
        "entry": dict(entry_ref),
        "first_touch": short_first_touch,
        "listing_regime": listing_regime,
        "mae_bps": format_exact_fraction(short_mae),
        "mae_trade": dict(short_mae_trade),
        "max_intertrade_gap_ms": max_intertrade_gap_ms,
        "mfe_bps": format_exact_fraction(short_mfe),
        "mfe_trade": dict(short_mfe_trade),
        "parent_article_id": parent_article_id,
        "state": "complete",
        "symbol": symbol,
        "t0": dict(t0_ref),
        "terminal_bps": format_exact_fraction(last_endpoint_short_bps),
        "touch_trade": dict(short_touch_trade) if short_touch_trade is not None else None,
    }
    return [long_row, short_row]


# -----------------------------------------------------------------------------
# Article AST Table Extraction & Ledger Verification (Independent of scripts/)
# -----------------------------------------------------------------------------


def _extract_article_ast_text(node: Any) -> str:
    if isinstance(node, dict):
        if "node" in node and node["node"] == "text":
            return str(node["text"]) if "text" in node else ""
        children = node["child"] if "child" in node and isinstance(node["child"], list) else []
        return "".join(_extract_article_ast_text(c) for c in children)
    if isinstance(node, list):
        return "".join(_extract_article_ast_text(c) for c in node)
    return ""


def _parse_article_ast_tables(body_obj: Any) -> list[list[list[str]]]:
    table_nodes: list[dict[str, Any]] = []

    def _find_tables(node: Any) -> None:
        if isinstance(node, dict):
            if "tag" in node and node["tag"] == "table":
                table_nodes.append(node)
            if "child" in node and isinstance(node["child"], list):
                for c in node["child"]:
                    _find_tables(c)
        elif isinstance(node, list):
            for c in node:
                _find_tables(c)

    _find_tables(body_obj)

    parsed_tables: list[list[list[str]]] = []
    for tbl in table_nodes:
        rows: list[list[str]] = []

        def _find_rows(node: Any) -> None:
            if isinstance(node, dict):
                if "tag" in node and node["tag"] == "tr":
                    cells: list[str] = []
                    children = (
                        node["child"] if "child" in node and isinstance(node["child"], list) else []
                    )
                    for c in children:
                        if isinstance(c, dict) and "tag" in c and c["tag"] in ("td", "th"):
                            cells.append(_extract_article_ast_text(c).strip())
                    if cells:
                        rows.append(cells)
                if "child" in node and isinstance(node["child"], list):
                    for c in node["child"]:
                        _find_rows(c)
            elif isinstance(node, list):
                for c in node:
                    _find_rows(c)

        _find_rows(tbl)
        if rows:
            parsed_tables.append(rows)
    return parsed_tables


def verify_and_scope_ledger_rows(
    ledger_path: Path,
    jb_child_rows: list[dict[str, Any]],
    ja_root: Path,
    ja_summary: dict[str, Any],
    project_root: Path | None = None,
    expected_universe_count: int = 281,
    expected_selected_count: int = 71,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Verify ledger 12-column schema, 281-key bijection with J-B, and article AST evidence for selected rows."""
    proj = project_root if project_root is not None else resolve_project_root()
    if os.path.islink(ledger_path) or not ledger_path.is_file():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_ledger_invalid:missing_or_symlink:{ledger_path}"
        )

    manifest_path = ja_root / "manifest.json"
    if os.path.islink(manifest_path) or not manifest_path.is_file():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_ledger_invalid:ja_manifest_missing:{manifest_path}"
        )
    ja_manifest = _parse_canonical_json_bytes(manifest_path.read_bytes(), "ja_manifest")
    ja_manifest_map: dict[str, dict[str, Any]] = {}
    for item in ja_manifest["artifacts"]:
        ja_manifest_map[str(item["relative_path"])] = item

    with open(ledger_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise Stage1_5JCDiagnosticError(
                "STOP=stage1_5j_c_ledger_invalid:empty_ledger"
            ) from exc
        if header != REQUIRED_LEDGER_COLUMNS:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_ledger_invalid:header_mismatch:{header}"
            )
        raw_rows: list[dict[str, str]] = []
        for row_idx, r in enumerate(reader, start=1):
            if len(r) != len(REQUIRED_LEDGER_COLUMNS):
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_invalid:column_count_row_{row_idx}:{len(r)}"
                )
            raw_rows.append(dict(zip(REQUIRED_LEDGER_COLUMNS, r)))

    seen_keys: set[tuple[str, str]] = set()
    for r in raw_rows:
        key = (r["parent_article_id"], r["symbol"])
        if key in seen_keys:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_ledger_invalid:duplicate_key:{key}"
            )
        seen_keys.add(key)

    jb_keys: set[tuple[str, str]] = set()
    for cr in jb_child_rows:
        jb_k = (str(cr["source_article_id"]), str(cr["symbol"]))
        if jb_k in jb_keys:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_ledger_invalid:duplicate_jb_key:{jb_k}"
            )
        jb_keys.add(jb_k)

    if seen_keys != jb_keys or len(raw_rows) != expected_universe_count:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_ledger_bijection_mismatch:ledger={len(raw_rows)}:jb={len(jb_keys)}"
        )

    sorted_rows = sorted(raw_rows, key=lambda x: (x["parent_article_id"], x["symbol"]))
    universe_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []

    crypto_headers = {
        "Project Info",
        "Project Information",
        "Smart Contract Address",
        "Total Supply",
        "Max Supply",
    }

    for r in sorted_rows:
        pid = r["parent_article_id"]
        sym = r["symbol"]
        a_cls = r["asset_class"]
        l_reg = r["listing_regime"]
        c_status = r["classification_status"]

        if (
            not HEX32_REGEX.match(pid)
            or not sym
            or not sym.isupper()
            or a_cls not in ALLOWED_ASSET_CLASSES
            or l_reg not in ALLOWED_LISTING_REGIMES
            or c_status not in ALLOWED_CLASSIFICATION_STATUS
        ):
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_ledger_invalid:enum_or_key:{pid}:{sym}"
            )

        in_scope = (
            a_cls == "crypto"
            and l_reg in ("standard", "pre_market")
            and c_status == "confirmed"
        )
        if a_cls == "crypto" and c_status != "confirmed":
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_ledger_invalid:unconfirmed_crypto:{pid}:{sym}"
            )

        u_row: dict[str, Any] = {
            "asset_class": a_cls,
            "classification_status": c_status,
            "in_scope": in_scope,
            "listing_regime": l_reg,
            "parent_article_id": pid,
            "symbol": sym,
        }
        universe_rows.append(u_row)

        if in_scope:
            exp_det_rel_in_ja = f"raw/article_details/{pid}.json"
            if exp_det_rel_in_ja not in ja_manifest_map:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:detail_not_in_ja_manifest:{pid}"
                )
            manifest_entry = ja_manifest_map[exp_det_rel_in_ja]
            src_rel = r["source_relative_path"]
            src_sha = r["source_sha256"]
            src_path = proj / src_rel
            expected_det_path = ja_root / exp_det_rel_in_ja

            if (
                os.path.islink(src_path)
                or not src_path.is_file()
                or src_path.resolve() != expected_det_path.resolve()
            ):
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:detail_path:{src_rel}"
                )
            actual_det_sha = _sha256_file(src_path)
            if actual_det_sha != src_sha or actual_det_sha != manifest_entry["sha256"]:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:detail_sha:{pid}"
                )

            try:
                det_obj = json.loads(src_path.read_text(encoding="utf-8"))
                det_data = det_obj["data"]
                title = str(det_data["title"])
                body_obj = json.loads(str(det_data["body"]))
            except Exception as exc:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:detail_json:{pid}:{exc}"
                ) from exc

            t_lower = title.lower()
            if "pre-market" in t_lower:
                exp_regime = "pre_market"
            elif "pre-ipo" in t_lower:
                exp_regime = "pre_ipo"
            else:
                exp_regime = "standard"
            if exp_regime != l_reg:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:regime:{pid}:{sym}:{exp_regime}!={l_reg}"
                )

            tables = _parse_article_ast_tables(body_obj)
            try:
                t_idx = int(r["table_index"])
                c_idx = int(r["symbol_column_index"])
            except ValueError as exc:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:indices:{pid}:{sym}"
                ) from exc

            if not (0 <= t_idx < len(tables)):
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:table_index:{pid}:{sym}:{t_idx}"
                )
            tbl = tables[t_idx]
            col_cells = [row[c_idx] if len(row) > c_idx else "" for row in tbl]
            if not any(sym.upper() in cell.upper().replace(" ", "") for cell in col_cells):
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:symbol_column:{pid}:{sym}"
                )

            hdr = r["field_header"]
            raw_cell = r["raw_cell_value"]
            loc = r["evidence_locator"]
            exp_loc = f"table[{t_idx}].col[{c_idx}].row['{hdr}']"
            if hdr not in crypto_headers or not raw_cell or loc != exp_loc:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:locator_or_header:{pid}:{sym}:{loc}"
                )
            row_map = {
                row[0]: (row[c_idx] if len(row) > c_idx else "")
                for row in tbl
                if len(row) > 0
            }
            if hdr not in row_map or row_map[hdr] != raw_cell:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_ledger_evidence_mismatch:cell_value:{pid}:{sym}"
                )

            selected_rows.append(u_row)

    if len(selected_rows) != expected_selected_count:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_ledger_selected_count_mismatch:{len(selected_rows)}!={expected_selected_count}"
        )

    return universe_rows, selected_rows


# -----------------------------------------------------------------------------
# J-C Local Package Admission & Bounded Reader
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class AdmittedJAContext:
    """Verified J-A admission context holding canonical root, manifest map, request map, and package records."""

    ja_root: Path
    manifest_by_path: dict[str, dict[str, Any]]
    request_by_id: dict[int, dict[str, Any]]
    package_by_key: dict[tuple[str, str, str], dict[str, Any]]
    admitted_object_ids: frozenset[int]


def build_admitted_ja_context(ja_root: Path, ja_summary: dict[str, Any]) -> AdmittedJAContext:
    """Build verified J-A package admission lookup from an already strict-loaded J-A root and summary."""
    if os.path.islink(ja_root) or not ja_root.is_dir():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:ja_root_invalid:{ja_root}"
        )
    manifest_file = ja_root / "manifest.json"
    if os.path.islink(manifest_file) or not manifest_file.is_file():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:ja_manifest_missing:{manifest_file}"
        )
    manifest_obj = _parse_canonical_json_bytes(manifest_file.read_bytes(), "ja_manifest")
    manifest_by_path: dict[str, dict[str, Any]] = {}
    for art in manifest_obj["artifacts"]:
        manifest_by_path[str(art["relative_path"])] = art

    request_by_id: dict[int, dict[str, Any]] = {}
    if "request_records" not in ja_summary or not isinstance(
        ja_summary["request_records"], list
    ):
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_authority_mismatch:ja_request_records_missing"
        )
    for req in ja_summary["request_records"]:
        request_by_id[int(req["request_id"])] = req

    package_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    obj_ids: set[int] = set()
    if "archive_package_records" not in ja_summary or not isinstance(
        ja_summary["archive_package_records"], list
    ):
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_authority_mismatch:ja_archive_package_records_missing"
        )
    for rec in ja_summary["archive_package_records"]:
        if not isinstance(rec, dict):
            raise Stage1_5JCDiagnosticError(
                "STOP=stage1_5j_c_package_record_invalid:not_a_dict"
            )
        k = (str(rec["parent_article_id"]), str(rec["symbol"]), str(rec["utc_date"]))
        if k in package_by_key:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_package_record_invalid:duplicate_key:{k}"
            )
        package_by_key[k] = rec
        obj_ids.add(id(rec))

    return AdmittedJAContext(
        ja_root=ja_root,
        manifest_by_path=manifest_by_path,
        request_by_id=request_by_id,
        package_by_key=package_by_key,
        admitted_object_ids=frozenset(obj_ids),
    )


class _JCStreamBoundedReader(io.RawIOBase):
    """Local J-C bounded raw stream enforcing EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES."""

    def __init__(self, raw: Any, chunk_limit: int) -> None:
        self._raw = raw
        self._limit = chunk_limit

    def readable(self) -> bool:
        return True

    def readinto(self, b: Any) -> int:
        req_len = len(b)
        if req_len > self._limit:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_stream_chunk_bytes_exceeded:{req_len}>{self._limit}"
            )
        readinto_fn = getattr(self._raw, "readinto", None)
        if callable(readinto_fn):
            return int(readinto_fn(b))
        data = self._raw.read(req_len)
        n = len(data)
        b[:n] = data
        return n

    def close(self) -> None:
        if not self.closed:
            super().close()
            self._raw.close()


@contextlib.contextmanager
def open_j_c_verified_package_stream(
    admitted_ja_context: AdmittedJAContext,
    pkg_record: dict[str, Any],
    expected_parent_article_id: str,
    expected_symbol: str,
    expected_utc_date: str,
) -> Generator[io.BufferedReader, None, None]:
    """Verify J-A package record provenance, manifest/request linkage, checksum, and ZIP caps, yielding bounded reader."""
    if not isinstance(pkg_record, dict) or id(pkg_record) not in admitted_ja_context.admitted_object_ids:
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_package_record_invalid:unadmitted_record"
        )

    key = (expected_parent_article_id, expected_symbol, expected_utc_date)
    if (
        key not in admitted_ja_context.package_by_key
        or admitted_ja_context.package_by_key[key] is not pkg_record
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_package_record_invalid:key_or_identity_mismatch:{key}"
        )

    p_id = pkg_record["parent_article_id"]
    sym = pkg_record["symbol"]
    utc_date = pkg_record["utc_date"]
    c_state = pkg_record["child_state"]
    logical_id = pkg_record["logical_archive_identity"]

    expected_logical = {
        "market": "futures_um",
        "metric": "aggTrades",
        "parent_article_id": expected_parent_article_id,
        "symbol": expected_symbol,
        "utc_date": expected_utc_date,
    }
    if (
        p_id != expected_parent_article_id
        or sym != expected_symbol
        or utc_date != expected_utc_date
        or logical_id != expected_logical
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_package_record_invalid:logical_identity_mismatch:{key}"
        )
    if c_state != "archive_verified_with_post_launch_rows":
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_package_record_invalid:child_state_not_verified:{c_state}"
        )

    zip_req_id = pkg_record["zip_request_id"]
    chk_req_id = pkg_record["checksum_request_id"]
    if (
        type(zip_req_id) is not int
        or type(chk_req_id) is not int
        or zip_req_id not in admitted_ja_context.request_by_id
        or chk_req_id not in admitted_ja_context.request_by_id
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_package_record_invalid:request_linkage_missing:{key}"
        )

    zip_rel = f"raw/archive/{sym}/{sym}-aggTrades-{utc_date}.zip"
    chk_rel = f"{zip_rel}.CHECKSUM"
    zip_req = admitted_ja_context.request_by_id[zip_req_id]
    chk_req = admitted_ja_context.request_by_id[chk_req_id]

    if (
        zip_req["request_kind"] != "archive"
        or zip_req["request_state"] != "response_persisted"
        or zip_req["response_relative_path"] != zip_rel
        or chk_req["request_kind"] != "checksum"
        or chk_req["request_state"] != "response_persisted"
        or chk_req["response_relative_path"] != chk_rel
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_package_record_invalid:request_record_mismatch:{key}"
        )

    if (
        zip_rel not in admitted_ja_context.manifest_by_path
        or chk_rel not in admitted_ja_context.manifest_by_path
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_package_record_invalid:manifest_member_missing:{key}"
        )
    zip_man = admitted_ja_context.manifest_by_path[zip_rel]
    chk_man = admitted_ja_context.manifest_by_path[chk_rel]

    if (
        zip_man["sha256"] != zip_req["response_sha256"]
        or zip_man["byte_count"] != zip_req["response_bytes"]
        or chk_man["sha256"] != chk_req["response_sha256"]
        or chk_man["byte_count"] != chk_req["response_bytes"]
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_package_record_invalid:manifest_request_sha_mismatch:{key}"
        )

    ja_root = admitted_ja_context.ja_root
    zip_path = ja_root / zip_rel
    chk_path = ja_root / chk_rel
    root_resolved = ja_root.resolve()

    if (
        _has_symlink_ancestor(zip_path, stop_at=ja_root)
        or _has_symlink_ancestor(chk_path, stop_at=ja_root)
        or not zip_path.is_file()
        or not chk_path.is_file()
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_zip_package_invalid:symlink_or_missing:{zip_path}"
        )
    try:
        zip_res = zip_path.resolve()
        chk_res = chk_path.resolve()
    except OSError as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_zip_package_invalid:resolve_failed:{exc}"
        ) from exc
    if not zip_res.is_relative_to(root_resolved) or not chk_res.is_relative_to(
        root_resolved
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_zip_package_invalid:path_escape:{zip_path}"
        )

    chk_bytes = chk_path.read_bytes()
    actual_chk_sha = _sha256_bytes(chk_bytes)
    if actual_chk_sha != chk_man["sha256"] or len(chk_bytes) != chk_man["byte_count"]:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_checksum_invalid:manifest_mismatch:{chk_path}"
        )
    try:
        chk_text = chk_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_checksum_invalid:utf8_error:{chk_path}"
        ) from exc
    parts = chk_text.strip().split()
    if (
        len(parts) != 2
        or not SHA256_REGEX.match(parts[0])
        or parts[1] != zip_path.name
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_checksum_invalid:format:{chk_path}"
        )
    expected_zip_sha = parts[0]
    actual_zip_sha = _sha256_file(zip_path)
    actual_zip_size = zip_path.stat().st_size
    if (
        actual_zip_sha != expected_zip_sha
        or actual_zip_sha != zip_man["sha256"]
        or actual_zip_size != zip_man["byte_count"]
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_checksum_invalid:zip_sha_mismatch:{zip_path}"
        )

    if not validate_zip_archive_package(
        zip_path,
        max_zip_bytes=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES,
        max_uncompressed_bytes=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
        max_ratio=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO,
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_zip_package_invalid:resource_caps:{zip_path}"
        )

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if len(names) != 1 or not names[0].endswith(".csv"):
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_zip_package_invalid:members:{names}"
                )
            with zf.open(names[0], "r") as raw_member:
                bounded = _JCStreamBoundedReader(
                    raw_member, EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES
                )
                buf = io.BufferedReader(
                    bounded,
                    buffer_size=EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
                )
                try:
                    yield buf
                finally:
                    buf.close()
    except Stage1_5JCDiagnosticError:
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_zip_package_invalid:corrupt_zip:{zip_path}:{exc}"
        ) from exc


def _iter_bounded_csv_rows_from_package(
    admitted_ja_context: AdmittedJAContext,
    pkg_record: dict[str, Any],
    expected_parent_article_id: str,
    expected_symbol: str,
    expected_utc_date: str,
) -> Generator[dict[str, Any], None, None]:
    """Stream all CSV rows to EOF with bounded line length <= 65,536 bytes and strict field checks."""
    max_line_bytes = EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES
    with open_j_c_verified_package_stream(
        admitted_ja_context,
        pkg_record,
        expected_parent_article_id=expected_parent_article_id,
        expected_symbol=expected_symbol,
        expected_utc_date=expected_utc_date,
    ) as buf:
        header_raw = buf.readline(max_line_bytes + 1)
        if not header_raw:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_csv_header_invalid:empty_file:{expected_symbol}:{expected_utc_date}"
            )
        if len(header_raw) > max_line_bytes or not header_raw.endswith(b"\n"):
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_csv_line_length_exceeded:header:{expected_symbol}:{expected_utc_date}"
            )
        try:
            header_text = header_raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_csv_encoding_invalid:header:{expected_symbol}"
            ) from exc
        header_cols = next(csv.reader([header_text]))
        if header_cols != REQUIRED_CSV_HEADER:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_csv_header_invalid:{header_cols}"
            )

        phys_row = 0
        while True:
            raw_line = buf.readline(max_line_bytes + 1)
            if not raw_line:
                break
            if len(raw_line) > max_line_bytes:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_csv_line_length_exceeded:{expected_symbol}:{expected_utc_date}:{phys_row + 1}"
                )
            try:
                line_text = raw_line.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_csv_encoding_invalid:{expected_symbol}:{phys_row + 1}"
                ) from exc
            parsed_rows = list(csv.reader([line_text]))
            if len(parsed_rows) != 1 or len(parsed_rows[0]) != 7:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_csv_row_malformed:{expected_symbol}:{phys_row + 1}"
                )
            cols = parsed_rows[0]
            phys_row += 1
            tid = _parse_nonneg_int_str(cols[0], "agg_trade_id")
            fid = _parse_nonneg_int_str(cols[3], "first_trade_id")
            lid = _parse_nonneg_int_str(cols[4], "last_trade_id")
            ts = _parse_nonneg_int_str(cols[5], "transact_time")
            yield {
                "utc_date": expected_utc_date,
                "physical_row": phys_row,
                "agg_trade_id": tid,
                "price": cols[1],
                "quantity": cols[2],
                "first_trade_id": fid,
                "last_trade_id": lid,
                "transact_time": ts,
                "is_buyer_maker": cols[6],
            }


def stream_and_reduce_child_packages(
    admitted_ja_context: AdmittedJAContext,
    parent_article_id: str,
    symbol: str,
    listing_regime: str,
    j_a_parent_state: str,
    anchor_state: str,
    symbol_launch_time_ms: int | None,
    expected_anchor_time_ms: int | None,
    expected_anchor_price: str | None,
    protocol: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Admit required J-A packages for a selected child, stream to EOF, and reduce to long/short Child rows."""
    proto = protocol if protocol is not None else EXPECTED_PROTOCOL_OBJECT
    horizon_ms = int(proto["horizon_ms"])

    if j_a_parent_state != "coverage_complete":
        return _make_gap_child_pair(
            parent_article_id,
            symbol,
            listing_regime,
            "inherited_j_a_parent_gap",
        )

    if anchor_state != "anchor_found":
        return _make_gap_child_pair(
            parent_article_id,
            symbol,
            listing_regime,
            "anchor_unavailable",
        )

    if (
        type(symbol_launch_time_ms) is not int
        or type(expected_anchor_time_ms) is not int
        or not isinstance(expected_anchor_price, str)
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_anchor_replay_mismatch:missing_anchor_fields:{parent_article_id}:{symbol}"
        )

    required_dates = compute_required_utc_dates(expected_anchor_time_ms, horizon_ms)
    anchor_date = required_dates[0]
    anchor_key = (parent_article_id, symbol, anchor_date)
    if anchor_key not in admitted_ja_context.package_by_key:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_package_record_invalid:anchor_package_missing:{anchor_key}"
        )
    anchor_pkg = admitted_ja_context.package_by_key[anchor_key]
    if anchor_pkg["child_state"] != "archive_verified_with_post_launch_rows":
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_package_record_invalid:anchor_package_unverified:{anchor_key}"
        )

    missing_later_package = False
    for d in required_dates[1:]:
        k = (parent_article_id, symbol, d)
        if (
            k not in admitted_ja_context.package_by_key
            or admitted_ja_context.package_by_key[k]["child_state"]
            != "archive_verified_with_post_launch_rows"
        ):
            missing_later_package = True

    if missing_later_package:
        # Still stream anchor package to EOF to verify integrity and extract exact t0 TradeRef
        expected_anchor_dec = _parse_positive_finite_decimal_str(
            expected_anchor_price, "expected_anchor_price"
        )
        t0_ref: dict[str, Any] | None = None
        prev_tid: int | None = None
        prev_ts: int | None = None
        for tr in _iter_bounded_csv_rows_from_package(
            admitted_ja_context,
            anchor_pkg,
            expected_parent_article_id=parent_article_id,
            expected_symbol=symbol,
            expected_utc_date=anchor_date,
        ):
            tid = int(tr["agg_trade_id"])
            ts = int(tr["transact_time"])
            fid = int(tr["first_trade_id"])
            lid = int(tr["last_trade_id"])
            if fid > lid or str(tr["is_buyer_maker"]) not in (
                "true",
                "false",
                "True",
                "False",
            ):
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_csv_row_malformed:{symbol}"
                )
            day_start, day_end = _utc_date_bounds_ms(anchor_date)
            if not (day_start <= ts < day_end):
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_csv_date_bounds_invalid:{symbol}:{anchor_date}:{ts}"
                )
            p_dec = _parse_positive_finite_decimal_str(str(tr["price"]), "price")
            _parse_positive_finite_decimal_str(str(tr["quantity"]), "quantity")
            if prev_tid is not None and tid <= prev_tid:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_csv_agg_trade_id_order_invalid:{symbol}"
                )
            if prev_ts is not None and ts < prev_ts:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_csv_timestamp_order_invalid:{symbol}"
                )
            prev_tid = tid
            prev_ts = ts
            if t0_ref is None and ts >= symbol_launch_time_ms:
                if (
                    ts != expected_anchor_time_ms
                    or p_dec != expected_anchor_dec
                    or ts - symbol_launch_time_ms
                    > EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS
                ):
                    raise Stage1_5JCDiagnosticError(
                        f"STOP=stage1_5j_c_anchor_replay_mismatch:{symbol}"
                    )
                t0_ref = _make_trade_ref(
                    anchor_date,
                    int(tr["physical_row"]),
                    tid,
                    ts,
                    str(tr["price"]),
                )
        if t0_ref is None:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_anchor_replay_missing:{parent_article_id}:{symbol}"
            )
        return _make_gap_child_pair(
            parent_article_id,
            symbol,
            listing_regime,
            "required_package_unavailable",
            t0_ref=t0_ref,
        )

    def _chained_trade_stream() -> Generator[dict[str, Any], None, None]:
        for d in required_dates:
            pkg = admitted_ja_context.package_by_key[(parent_article_id, symbol, d)]
            yield from _iter_bounded_csv_rows_from_package(
                admitted_ja_context,
                pkg,
                expected_parent_article_id=parent_article_id,
                expected_symbol=symbol,
                expected_utc_date=d,
            )

    return reduce_child_time_path_from_trades(
        parent_article_id=parent_article_id,
        symbol=symbol,
        listing_regime=listing_regime,
        symbol_launch_time_ms=symbol_launch_time_ms,
        expected_anchor_time_ms=expected_anchor_time_ms,
        expected_anchor_price=expected_anchor_price,
        trades=_chained_trade_stream(),
        protocol=proto,
    )


# -----------------------------------------------------------------------------
# Source/Input Seals and Custodian Release -> Derived Authorization
# -----------------------------------------------------------------------------


def _make_file_seal(project_root: Path, rel_path: str) -> dict[str, Any]:
    full = project_root / rel_path
    if _has_symlink_ancestor(full, stop_at=project_root) or not full.is_file():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:missing_or_symlink:{rel_path}"
        )
    raw = full.read_bytes()
    return {
        "relative_path": rel_path,
        "sha256": _sha256_bytes(raw),
        "size_bytes": len(raw),
    }


def compute_source_bundle_seals_and_sha256(
    project_root: Path | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Compute sorted 11-file source_files FileSeal list and AUTHORIZED_SOURCE_BUNDLE_SHA256."""
    proj = project_root if project_root is not None else resolve_project_root()
    seals: list[dict[str, Any]] = []
    for rel in ALL_11_SOURCE_RELATIVE_PATHS:
        seal = _make_file_seal(proj, rel)
        if rel in FROZEN_SOURCE_FILE_HASHES:
            if seal["sha256"] != FROZEN_SOURCE_FILE_HASHES[rel]:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_authority_mismatch:frozen_source_sha_mismatch:{rel}"
                )
        seals.append(seal)
    bundle_bytes = _dump_canonical_json_bytes(seals)
    return seals, _sha256_bytes(bundle_bytes)


def compute_input_file_seals(project_root: Path | None = None) -> list[dict[str, Any]]:
    """Compute and verify sorted 9-file input_files FileSeal list."""
    proj = project_root if project_root is not None else resolve_project_root()
    load_and_verify_protocol(proj / PROTOCOL_RELATIVE_PATH)
    seals: list[dict[str, Any]] = []
    for rel in ALL_9_INPUT_RELATIVE_PATHS:
        seal = _make_file_seal(proj, rel)
        if seal["sha256"] != FROZEN_INPUT_FILE_HASHES[rel]:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_mismatch:frozen_input_sha_mismatch:{rel}"
            )
        seals.append(seal)
    return seals


def _verify_two_space_sidecar(target_file: Path, sidecar_file: Path) -> str:
    if os.path.islink(target_file) or not target_file.is_file():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:target_missing_or_symlink:{target_file}"
        )
    if os.path.islink(sidecar_file) or not sidecar_file.is_file():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:sidecar_missing_or_symlink:{sidecar_file}"
        )
    actual_sha = _sha256_file(target_file)
    expected_sidecar = f"{actual_sha}  {target_file.name}\n".encode("ascii")
    if sidecar_file.read_bytes() != expected_sidecar:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:sidecar_mismatch:{sidecar_file}"
        )
    return actual_sha


def _parse_11_line_user_approval(raw_bytes: bytes) -> dict[str, str]:
    try:
        text = raw_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_authority_mismatch:approval_not_ascii"
        ) from exc
    if not text.endswith("\n") or "\r" in text:
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_authority_mismatch:approval_newline_invalid"
        )
    lines = text[:-1].split("\n")
    if len(lines) != 11:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:approval_line_count:{len(lines)}"
        )
    parsed: dict[str, str] = {}
    for idx, expected_key in enumerate(APPROVAL_ORDERED_KEYS):
        line = lines[idx]
        if "=" not in line or line != line.strip():
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_mismatch:approval_line_syntax:{idx + 1}"
            )
        k, v = line.split("=", 1)
        if k != expected_key or not v or v != v.strip():
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_mismatch:approval_key_order:{k}!={expected_key}"
            )
        parsed[k] = v
    return parsed


def validate_run_id_grammar(run_id: str) -> None:
    """Validate run_id matches stage1_5j_c_launch_time_path_feasibility_YYYYMMDDTHHMMSSZ with real UTC date."""
    if not isinstance(run_id, str):
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_authority_mismatch:run_id_type")
    m = RUN_ID_REGEX.match(run_id)
    if not m:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:run_id_grammar:{run_id}"
        )
    try:
        datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:run_id_invalid_utc:{run_id}"
        ) from exc


def verify_and_derive_run_authorization(
    operation: str,
    run_id: str,
    project_root: Path | None = None,
    authority_dir: Path | None = None,
) -> dict[str, Any]:
    """Verify external user approval + Custodian release before any loader, then derive run_authorization.json."""
    if RISK_LIVE_TRADING_ENABLED is not False:
        raise Stage1_5JCDiagnosticError("STOP=configs_risk_live_trading_enabled_must_be_false")

    if operation not in ALLOWED_OPERATIONS:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:unsupported_operation:{operation}"
        )
    validate_run_id_grammar(run_id)

    proj = project_root if project_root is not None else resolve_project_root()
    design_seal = _make_file_seal(proj, APPROVED_DESIGN_RELATIVE_PATH)
    if design_seal["sha256"] != APPROVED_DESIGN_SHA256:
        raise Stage1_5JCDiagnosticError("STOP=design_authority_mismatch")

    plan_seal = _make_file_seal(proj, APPROVED_PLAN_RELATIVE_PATH)
    plan_sha = plan_seal["sha256"]

    auth_dir = (
        authority_dir
        if authority_dir is not None
        else (proj / ".git" / "plan-execution" / "stage1_5j_c" / plan_sha / run_id)
    )
    if _has_symlink_ancestor(auth_dir, stop_at=proj if auth_dir.is_relative_to(proj) else None):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:authority_dir_symlink:{auth_dir}"
        )

    approval_file = auth_dir / "user_receipt_generation_approval.txt"
    approval_sidecar = auth_dir / "user_receipt_generation_approval.txt.sha256"
    release_file = auth_dir / "authorization_release.json"
    release_sidecar = auth_dir / "authorization_release.json.sha256"

    if (
        not approval_file.is_file()
        or not approval_sidecar.is_file()
        or not release_file.is_file()
        or not release_sidecar.is_file()
    ):
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_independent_approval_release_unavailable"
        )

    approval_sha = _verify_two_space_sidecar(approval_file, approval_sidecar)
    release_sha = _verify_two_space_sidecar(release_file, release_sidecar)

    approval_bytes = approval_file.read_bytes()
    approval_map = _parse_11_line_user_approval(approval_bytes)
    release_obj = _parse_canonical_json_bytes(
        release_file.read_bytes(), "authorization_release"
    )
    if not isinstance(release_obj, dict) or set(release_obj.keys()) != RELEASE_EXACT_KEYS:
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_authority_mismatch:release_keyset_mismatch"
        )

    source_seals, bundle_sha = compute_source_bundle_seals_and_sha256(proj)
    input_seals = compute_input_file_seals(proj)

    # Validate 11-line approval values
    if (
        approval_map["APPROVED_J_C_PLAN_RELATIVE_PATH"] != APPROVED_PLAN_RELATIVE_PATH
        or approval_map["APPROVED_J_C_PLAN_SHA256"] != plan_sha
        or approval_map["AUTHORIZED_SOURCE_BUNDLE_SHA256"] != bundle_sha
        or approval_map["AUTHORIZED_OPERATION"] != operation
        or approval_map["AUTHORIZED_RUN_ID"] != run_id
    ):
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_authority_mismatch:approval_tuple_mismatch"
        )
    for perm_k in (
        "NETWORK_ALLOWED",
        "SIGNAL_ALLOWED",
        "PAPER_TRADING_ALLOWED",
        "LIVE_TRADING_ALLOWED",
        "EXECUTION_ALLOWED",
    ):
        if approval_map[perm_k] != "false":
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_mismatch:approval_permission_not_false:{perm_k}"
            )

    output_root_str = approval_map["AUTHORIZED_OUTPUT_ROOT"]
    expected_canonical_rel_root = f"{OUTPUT_PARENT_RELATIVE_PATH}/{run_id}"
    if operation == "offline_time_path_diagnostic_once":
        if output_root_str != expected_canonical_rel_root:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_mismatch:diagnostic_output_root_invalid:{output_root_str}"
            )
        target_root_path = proj / output_root_str
        if _has_symlink_ancestor(target_root_path, stop_at=proj):
            raise Stage1_5JCDiagnosticError(
                "STOP=stage1_5j_c_authority_mismatch:diagnostic_output_root_symlink"
            )
    else:
        target_root_path = Path(output_root_str)
        if not target_root_path.is_absolute() or target_root_path.name != run_id:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_mismatch:validation_output_root_not_absolute:{output_root_str}"
            )
        if _has_symlink_ancestor(target_root_path):
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_mismatch:validation_output_root_symlink:{output_root_str}"
            )
        proj_resolved = proj.resolve()
        parent_resolved = target_root_path.parent.resolve() if target_root_path.parent.exists() else target_root_path.resolve()
        if parent_resolved == proj_resolved or parent_resolved.is_relative_to(proj_resolved):
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_mismatch:validation_output_root_inside_repo:{output_root_str}"
            )

    if target_root_path.exists() or os.path.islink(target_root_path):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_output_exists:{target_root_path}"
        )

    rel_prefix = f".git/plan-execution/stage1_5j_c/{plan_sha}/{run_id}"
    expected_approval_seal = {
        "relative_path": f"{rel_prefix}/user_receipt_generation_approval.txt",
        "sha256": approval_sha,
        "size_bytes": len(approval_bytes),
    }
    expected_release_seal = {
        "relative_path": f"{rel_prefix}/authorization_release.json",
        "sha256": release_sha,
        "size_bytes": len(release_file.read_bytes()),
    }

    if (
        release_obj["release_schema_version"] != 1
        or type(release_obj["release_schema_version"]) is not int
        or release_obj["release_state"] != "user_message_verified_and_released"
        or release_obj["user_receipt_generation_approval"] != expected_approval_seal
        or release_obj["design"] != design_seal
        or release_obj["plan"] != plan_seal
        or release_obj["authorized_source_bundle_sha256"] != bundle_sha
        or release_obj["operation"] != operation
        or release_obj["run_id"] != run_id
        or release_obj["output_root"] != output_root_str
    ):
        raise Stage1_5JCDiagnosticError(
            "STOP=stage1_5j_c_authority_mismatch:release_tuple_mismatch"
        )

    for bool_k in (
        "network_allowed",
        "signal_allowed",
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_allowed",
    ):
        if release_obj[bool_k] is not False or type(release_obj[bool_k]) is not bool:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_mismatch:release_permission_not_false:{bool_k}"
            )

    derived_file = auth_dir / "run_authorization.json"
    derived_sidecar = auth_dir / "run_authorization.json.sha256"
    if derived_file.exists() or derived_sidecar.exists():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_authority_mismatch:run_authorization_already_exists:{derived_file}"
        )

    derived_obj: dict[str, Any] = {
        "authorization_release": expected_release_seal,
        "authorized_source_bundle_sha256": bundle_sha,
        "design": design_seal,
        "execution_allowed": False,
        "input_files": input_seals,
        "live_trading_allowed": False,
        "network_allowed": False,
        "operation": operation,
        "output_root": output_root_str,
        "paper_trading_allowed": False,
        "plan": plan_seal,
        "run_id": run_id,
        "signal_allowed": False,
        "source_files": source_seals,
        "user_receipt_generation_approval": expected_approval_seal,
    }
    derived_bytes = _dump_canonical_json_bytes(derived_obj)
    derived_sha = _sha256_bytes(derived_bytes)
    derived_file.write_bytes(derived_bytes)
    derived_sidecar.write_bytes(
        f"{derived_sha}  run_authorization.json\n".encode("ascii")
    )
    _verify_two_space_sidecar(derived_file, derived_sidecar)
    return derived_obj


# -----------------------------------------------------------------------------
# Task 3: Child -> Parent -> Group Projection, Review Rendering, Atomic Publish,
# Strict Domain Loader Replay, and Independent Oracles
# -----------------------------------------------------------------------------


EXPECTED_UNIVERSE_COUNT = 281
EXPECTED_SELECTED_COUNT = 71

MANIFEST_EXACT_KEYS = {
    "profile_id",
    "profile_contract_version",
    "artifact_kind",
    "run_id",
    "files",
}
SUMMARY_EXACT_KEYS = {
    "profile_id",
    "profile_contract_version",
    "artifact_kind",
    "run_id",
    "authority",
    "protocol",
    "permissions",
    "analysis_state",
    "universe_rows",
    "child_rows",
    "parent_rows",
    "group_rows",
}
AUTHORITY_EXACT_KEYS = {
    "design",
    "plan",
    "user_receipt_generation_approval",
    "authorization_release",
    "run_authorization",
    "source_files",
    "input_files",
}
PERMISSIONS_EXACT_KEYS = set(CANONICAL_PERMISSIONS.keys())


def compute_distribution(values: list[Fraction]) -> dict[str, Any]:
    """Compute exact rational Distribution (n, mean, median, min, max, p10, p25, p75, p90) with nearest-rank quantiles."""
    n = len(values)
    if n == 0:
        return {
            "max": None,
            "mean": None,
            "median": None,
            "min": None,
            "n": 0,
            "p10": None,
            "p25": None,
            "p75": None,
            "p90": None,
        }
    for v in values:
        if not isinstance(v, Fraction):
            raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_distribution_requires_fraction")
    s = sorted(values)
    mean_val = sum(s, Fraction(0, 1)) / Fraction(n, 1)
    if n % 2 == 1:
        median_val = s[n // 2]
    else:
        median_val = (s[n // 2 - 1] + s[n // 2]) / Fraction(2, 1)

    def _nearest_rank(num: int, den: int) -> Fraction:
        rank = (num * n + den - 1) // den
        return s[rank - 1]

    return {
        "max": format_exact_fraction(s[-1]),
        "mean": format_exact_fraction(mean_val),
        "median": format_exact_fraction(median_val),
        "min": format_exact_fraction(s[0]),
        "n": n,
        "p10": format_exact_fraction(_nearest_rank(1, 10)),
        "p25": format_exact_fraction(_nearest_rank(1, 4)),
        "p75": format_exact_fraction(_nearest_rank(3, 4)),
        "p90": format_exact_fraction(_nearest_rank(9, 10)),
    }


def _median_fraction(values: list[Fraction]) -> Fraction:
    s = sorted(values)
    n = len(s)
    if n == 0:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_empty_median")
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / Fraction(2, 1)


def project_parents_and_groups(
    child_rows: list[dict[str, Any]],
    cost_bps_scenarios: list[int] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministically reduce Child rows into Parent rows and the 4 fixed Group rows."""
    costs_list = (
        cost_bps_scenarios
        if cost_bps_scenarios is not None
        else list(EXPECTED_PROTOCOL_OBJECT["friction_bps"])
    )
    if costs_list != [50, 80, 150]:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_invalid_cost_scenarios:{costs_list}"
        )

    # Group children by (parent_article_id, listing_regime, direction)
    by_parent_key: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for c in child_rows:
        pid = str(c["parent_article_id"])
        reg = str(c["listing_regime"])
        direction = str(c["direction"])
        if reg not in ("pre_market", "standard") or direction not in ("long", "short"):
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_invalid_child_regime_or_direction:{reg}:{direction}"
            )
        k = (pid, reg, direction)
        if k not in by_parent_key:
            by_parent_key[k] = []
        by_parent_key[k].append(c)

    parent_rows: list[dict[str, Any]] = []
    for k in sorted(by_parent_key.keys()):
        pid, reg, direction = k
        members = sorted(by_parent_key[k], key=lambda x: str(x["symbol"]))
        symbols = [str(m["symbol"]) for m in members]
        if len(symbols) != len(set(symbols)):
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_duplicate_child_in_parent:{k}"
            )
        utc_dates_set: set[str] = set()
        complete_members: list[dict[str, Any]] = []
        n_gap = 0
        for m in members:
            t0_obj = m["t0"]
            if t0_obj is not None:
                utc_dates_set.add(str(t0_obj["utc_date"]))
            if m["state"] == "complete":
                complete_members.append(m)
            else:
                n_gap += 1
        n_complete = len(complete_members)
        if n_gap == 0 and n_complete > 0:
            p_state = "complete"
            term_vals = [parse_exact_fraction(str(m["terminal_bps"])) for m in complete_members]
            mfe_vals = [parse_exact_fraction(str(m["mfe_bps"])) for m in complete_members]
            mae_vals = [parse_exact_fraction(str(m["mae_bps"])) for m in complete_members]
            tc = {"neither": 0, "risk": 0, "target": 0}
            for m in complete_members:
                ft = str(m["first_touch"])
                if ft not in tc:
                    raise Stage1_5JCDiagnosticError(
                        f"STOP=stage1_5j_c_invalid_first_touch_in_complete_child:{ft}"
                    )
                tc[ft] += 1
            p_row: dict[str, Any] = {
                "direction": direction,
                "listing_regime": reg,
                "mae_bps": format_exact_fraction(_median_fraction(mae_vals)),
                "mfe_bps": format_exact_fraction(_median_fraction(mfe_vals)),
                "n_complete": n_complete,
                "n_gap": 0,
                "parent_article_id": pid,
                "state": p_state,
                "symbols": symbols,
                "terminal_bps": format_exact_fraction(_median_fraction(term_vals)),
                "touch_counts": tc,
                "utc_dates": sorted(utc_dates_set),
            }
        else:
            p_row = {
                "direction": direction,
                "listing_regime": reg,
                "mae_bps": None,
                "mfe_bps": None,
                "n_complete": n_complete,
                "n_gap": n_gap,
                "parent_article_id": pid,
                "state": "gap",
                "symbols": symbols,
                "terminal_bps": None,
                "touch_counts": None,
                "utc_dates": sorted(utc_dates_set),
            }
        parent_rows.append(p_row)

    group_rows: list[dict[str, Any]] = []
    for reg, direction in (
        ("pre_market", "long"),
        ("pre_market", "short"),
        ("standard", "long"),
        ("standard", "short"),
    ):
        g_children = [
            c
            for c in child_rows
            if c["listing_regime"] == reg and c["direction"] == direction
        ]
        g_parents = [
            p
            for p in parent_rows
            if p["listing_regime"] == reg and p["direction"] == direction
        ]

        comp_children = [c for c in g_children if c["state"] == "complete"]
        gap_children = [c for c in g_children if c["state"] != "complete"]
        comp_parents = [p for p in g_parents if p["state"] == "complete"]
        gap_parents = [p for p in g_parents if p["state"] != "complete"]

        c_term = [parse_exact_fraction(str(c["terminal_bps"])) for c in comp_children]
        c_mfe = [parse_exact_fraction(str(c["mfe_bps"])) for c in comp_children]
        c_mae = [parse_exact_fraction(str(c["mae_bps"])) for c in comp_children]

        p_term = [parse_exact_fraction(str(p["terminal_bps"])) for p in comp_parents]
        p_mfe = [parse_exact_fraction(str(p["mfe_bps"])) for p in comp_parents]
        p_mae = [parse_exact_fraction(str(p["mae_bps"])) for p in comp_parents]

        child_stats = {
            "mae": compute_distribution(c_mae),
            "mfe": compute_distribution(c_mfe),
            "n_complete": len(comp_children),
            "n_gap": len(gap_children),
            "n_total": len(g_children),
            "terminal": compute_distribution(c_term),
        }
        parent_stats = {
            "mae": compute_distribution(p_mae),
            "mfe": compute_distribution(p_mfe),
            "n_complete": len(comp_parents),
            "n_gap": len(gap_parents),
            "n_total": len(g_parents),
            "terminal": compute_distribution(p_term),
        }

        g_touch = {"neither": 0, "risk": 0, "target": 0}
        for c in comp_children:
            g_touch[str(c["first_touch"])] += 1

        if len(comp_parents) == 0:
            parent_touch_frac: dict[str, Any] = {
                "neither": None,
                "risk": None,
                "target": None,
            }
        else:
            n_cp = Fraction(len(comp_parents), 1)
            t_sum = sum(
                (
                    Fraction(int(p["touch_counts"]["target"]), int(p["n_complete"]))
                    for p in comp_parents
                ),
                Fraction(0, 1),
            )
            r_sum = sum(
                (
                    Fraction(int(p["touch_counts"]["risk"]), int(p["n_complete"]))
                    for p in comp_parents
                ),
                Fraction(0, 1),
            )
            n_sum = sum(
                (
                    Fraction(int(p["touch_counts"]["neither"]), int(p["n_complete"]))
                    for p in comp_parents
                ),
                Fraction(0, 1),
            )
            parent_touch_frac = {
                "neither": format_exact_fraction(n_sum / n_cp),
                "risk": format_exact_fraction(r_sum / n_cp),
                "target": format_exact_fraction(t_sum / n_cp),
            }

        cost_rows: list[dict[str, Any]] = []
        for cost_bps in costs_list:
            cost_frac = Fraction(cost_bps, 1)
            c_adj = [m - cost_frac for m in c_mfe]
            p_adj = [m - cost_frac for m in p_mfe]
            c_pos = sum(1 for v in c_adj if v > 0)
            p_pos = sum(1 for v in p_adj if v > 0)
            if len(g_children) == 0 or len(gap_children) > 0:
                sp_status = "evidence_insufficient"
            elif c_pos > 0:
                sp_status = "observed_space"
            else:
                sp_status = "no_observed_space"
            cost_rows.append(
                {
                    "child": compute_distribution(c_adj),
                    "child_positive": c_pos,
                    "cost_bps": cost_bps,
                    "parent": compute_distribution(p_adj),
                    "parent_positive": p_pos,
                    "space_status": sp_status,
                }
            )

        sorted_comp_parents = sorted(
            comp_parents,
            key=lambda p: (-parse_exact_fraction(str(p["mfe_bps"])), str(p["parent_article_id"])),
        )
        top1_ids = [str(p["parent_article_id"]) for p in sorted_comp_parents[:1]]
        top3_ids = [str(p["parent_article_id"]) for p in sorted_comp_parents[:3]]
        total_parent_mfe = sum(
            (parse_exact_fraction(str(p["mfe_bps"])) for p in sorted_comp_parents),
            Fraction(0, 1),
        )
        if total_parent_mfe <= 0:
            top1_share = None
            top3_share = None
        else:
            top1_mfe = sum(
                (parse_exact_fraction(str(p["mfe_bps"])) for p in sorted_comp_parents[:1]),
                Fraction(0, 1),
            )
            top3_mfe = sum(
                (parse_exact_fraction(str(p["mfe_bps"])) for p in sorted_comp_parents[:3]),
                Fraction(0, 1),
            )
            top1_share = format_exact_fraction(top1_mfe / total_parent_mfe)
            top3_share = format_exact_fraction(top3_mfe / total_parent_mfe)

        concentration = {
            "top1_parent_ids": top1_ids,
            "top1_share": top1_share,
            "top3_parent_ids": top3_ids,
            "top3_share": top3_share,
        }

        group_rows.append(
            {
                "child": child_stats,
                "concentration": concentration,
                "costs": cost_rows,
                "direction": direction,
                "listing_regime": reg,
                "parent": parent_stats,
                "parent_touch_fraction_mean": parent_touch_frac,
                "touch_counts": g_touch,
            }
        )

    return parent_rows, group_rows


def render_stage1_5j_c_review(summary: dict[str, Any]) -> str:
    """Render deterministic review_CN.md from summary dict per Design §6.2."""
    lines: list[str] = [
        "# Stage 1.5J-C 时间与路径诊断",
        f"run_id: {summary['run_id']}",
        f"profile_id: {summary['profile_id']}",
        f"artifact_kind: {summary['artifact_kind']}",
        f"analysis_state: {summary['analysis_state']}",
        "universe_children: 281",
        "selected_children: 71",
    ]
    for grp in summary["group_rows"]:
        c_stats = grp["child"]
        p_stats = grp["parent"]
        tc = grp["touch_counts"]
        lines.append(f"## {grp['listing_regime']} / {grp['direction']}")
        lines.append(
            f"children: {c_stats['n_total']}; complete: {c_stats['n_complete']}; gap: {c_stats['n_gap']}"
        )
        lines.append(
            f"parents: {p_stats['n_total']}; complete: {p_stats['n_complete']}; gap: {p_stats['n_gap']}"
        )
        lines.append(
            f"first_touch: target={tc['target']}; risk={tc['risk']}; neither={tc['neither']}"
        )
        for cost_row in grp["costs"]:
            lines.append(
                f"cost_bps={cost_row['cost_bps']}; space_status={cost_row['space_status']}"
            )
    lines.append(
        "Exploratory price-path diagnosis only; no alpha, execution, paper or live trading authority."
    )
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class PublishResult:
    """Returned by publish_stage1_5j_c_receipt_root ONLY after parent-directory fsync succeeds."""

    run_id: str
    artifact_kind: str
    operation: str
    final_root: str
    manifest_sha256: str
    summary_sha256: str
    review_sha256: str
    publish_terminal: str
    producer_returned_success: bool


def _fsync_file_descriptor(fd: int) -> None:
    os.fsync(fd)


def _fsync_directory(dir_path: Path) -> None:
    dir_fd = os.open(str(dir_path), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _atomic_rename_staging_to_final(staging_path: Path, final_path: Path) -> None:
    if os.path.lexists(final_path):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_output_exists:before_rename:{final_path}"
        )
    os.rename(staging_path, final_path)


def publish_stage1_5j_c_receipt_root(
    *,
    output_root: Path,
    run_id: str,
    artifact_kind: str,
    operation: str,
    manifest_bytes: bytes,
    summary_bytes: bytes,
    review_bytes: bytes,
    pre_publish_verify_callback: Any | None = None,
) -> PublishResult:
    """Single-process atomic publication with exclusive lock, staging, per-file fsync, staging fsync, rename, and parent fsync."""
    if os.path.lexists(output_root):
        raise Stage1_5JCDiagnosticError(f"STOP=stage1_5j_c_output_exists:{output_root}")

    parent_dir = output_root.parent
    if _has_symlink_ancestor(parent_dir):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_output_parent_symlink:{parent_dir}"
        )
    parent_dir.mkdir(parents=True, exist_ok=True)

    lock_path = parent_dir / f".{run_id}.lock"
    staging_path = parent_dir / f".{run_id}.staging"

    if os.path.lexists(lock_path):
        raise Stage1_5JCDiagnosticError(f"STOP=stage1_5j_c_lock_collision:{lock_path}")
    if os.path.lexists(staging_path):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_staging_collision:{staging_path}"
        )

    total_bytes = len(manifest_bytes) + len(summary_bytes) + len(review_bytes)
    if total_bytes > EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_output_root_bytes_exceeded:{total_bytes}"
        )

    try:
        st_vfs = os.statvfs(parent_dir)
        free_bytes = st_vfs.f_bavail * st_vfs.f_frsize
    except OSError as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_publish_io_error:statvfs:{exc}"
        ) from exc
    if free_bytes < EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_insufficient_free_disk_space:{free_bytes}"
        )

    try:
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_lock_collision:{lock_path}"
        ) from exc
    except OSError as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_publish_io_error:lock_open:{exc}"
        ) from exc

    rename_completed = False
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_lock_collision:flock:{lock_path}:{exc}"
            ) from exc

        os.mkdir(staging_path, 0o755)

        if callable(pre_publish_verify_callback):
            pre_publish_verify_callback()

        files_to_write = [
            ("manifest.json", manifest_bytes),
            ("review_CN.md", review_bytes),
            ("summary.json", summary_bytes),
        ]
        for fname, fbytes in files_to_write:
            fpath = staging_path / fname
            ffd = os.open(
                str(fpath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644
            )
            try:
                view = memoryview(fbytes)
                written = 0
                while written < len(view):
                    n = os.write(ffd, view[written:])
                    if n <= 0:
                        raise OSError(f"short write on {fpath}")
                    written += n
                _fsync_file_descriptor(ffd)
            finally:
                os.close(ffd)

        _fsync_directory(staging_path)
        _atomic_rename_staging_to_final(staging_path, output_root)
        rename_completed = True
        _fsync_directory(parent_dir)
    except Stage1_5JCDiagnosticError:
        raise
    except OSError as exc:
        if rename_completed:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_parent_directory_fsync_failed_after_rename:{output_root}:{exc}"
            ) from exc
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_publish_io_error:{exc}"
        ) from exc
    finally:
        try:
            os.close(lock_fd)
        except OSError:
            pass

    # Clean normal exit: remove lock file and fsync parent directory
    try:
        os.unlink(lock_path)
        _fsync_directory(parent_dir)
    except OSError as exc:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_parent_directory_fsync_failed_after_rename:lock_cleanup:{exc}"
        ) from exc

    return PublishResult(
        run_id=run_id,
        artifact_kind=artifact_kind,
        operation=operation,
        final_root=str(output_root),
        manifest_sha256=_sha256_bytes(manifest_bytes),
        summary_sha256=_sha256_bytes(summary_bytes),
        review_sha256=_sha256_bytes(review_bytes),
        publish_terminal="parent_directory_fsynced",
        producer_returned_success=True,
    )


def _load_upstream_ja_and_jb_for_replay(
    project_root: Path,
) -> tuple[Path, dict[str, Any], list[dict[str, Any]], int, int]:
    """Load canonical J-A root/summary and J-B child_rows via public strict loaders."""
    ja_root = project_root / J_A_ROOT_RELATIVE_PATH
    jb_root = project_root / J_B_ROOT_RELATIVE_PATH
    ja_summary = load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)
    jb_summary = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(
        jb_root
    )
    return (
        ja_root,
        ja_summary,
        list(jb_summary["child_rows"]),
        EXPECTED_UNIVERSE_COUNT,
        EXPECTED_SELECTED_COUNT,
    )


def compute_stage1_5j_c_summary_from_admitted_inputs(
    *,
    run_id: str,
    artifact_kind: str,
    authority_obj: dict[str, Any],
    protocol_obj: dict[str, Any],
    ja_root: Path,
    ja_summary: dict[str, Any],
    jb_child_rows: list[dict[str, Any]],
    ledger_path: Path,
    project_root: Path,
    expected_universe_count: int = EXPECTED_UNIVERSE_COUNT,
    expected_selected_count: int = EXPECTED_SELECTED_COUNT,
) -> dict[str, Any]:
    """Compute complete J-C summary dict from admitted upstream inputs."""
    universe_rows, selected_rows = verify_and_scope_ledger_rows(
        ledger_path=ledger_path,
        jb_child_rows=jb_child_rows,
        ja_root=ja_root,
        ja_summary=ja_summary,
        project_root=project_root,
        expected_universe_count=expected_universe_count,
        expected_selected_count=expected_selected_count,
    )
    admitted_ctx = build_admitted_ja_context(ja_root, ja_summary)
    jb_by_key = {
        (str(r["source_article_id"]), str(r["symbol"])): r for r in jb_child_rows
    }

    child_rows: list[dict[str, Any]] = []
    for u_row in sorted(
        selected_rows, key=lambda r: (str(r["parent_article_id"]), str(r["symbol"]))
    ):
        pid = str(u_row["parent_article_id"])
        sym = str(u_row["symbol"])
        reg = str(u_row["listing_regime"])
        jb_r = jb_by_key[(pid, sym)]
        pair = stream_and_reduce_child_packages(
            admitted_ja_context=admitted_ctx,
            parent_article_id=pid,
            symbol=sym,
            listing_regime=reg,
            j_a_parent_state=str(jb_r["j_a_parent_state"]),
            anchor_state=str(jb_r["anchor_state"]),
            symbol_launch_time_ms=jb_r["symbol_launch_time_ms"],
            expected_anchor_time_ms=jb_r["anchor_time_ms"],
            expected_anchor_price=jb_r["anchor_price"],
            protocol=protocol_obj,
        )
        child_rows.extend(pair)

    child_rows.sort(
        key=lambda r: (
            str(r["parent_article_id"]),
            str(r["symbol"]),
            str(r["direction"]),
        )
    )
    parent_rows, group_rows = project_parents_and_groups(
        child_rows, list(protocol_obj["friction_bps"])
    )

    if len(child_rows) > 0 and all(c["state"] == "complete" for c in child_rows):
        analysis_state = "time_path_described"
    else:
        analysis_state = "time_path_evidence_gap"

    permissions_obj = {k: False for k in sorted(PERMISSIONS_EXACT_KEYS)}

    return {
        "analysis_state": analysis_state,
        "artifact_kind": artifact_kind,
        "authority": authority_obj,
        "child_rows": child_rows,
        "group_rows": group_rows,
        "parent_rows": parent_rows,
        "permissions": permissions_obj,
        "profile_contract_version": PROFILE_CONTRACT_VERSION,
        "profile_id": PROFILE_ID,
        "protocol": protocol_obj,
        "run_id": run_id,
        "universe_rows": universe_rows,
    }


def build_stage1_5j_c_manifest(
    *,
    run_id: str,
    artifact_kind: str,
    summary_bytes: bytes,
    review_bytes: bytes,
) -> dict[str, Any]:
    """Build canonical J-C manifest.json dict sealing review_CN.md and summary.json."""
    return {
        "artifact_kind": artifact_kind,
        "files": [
            {
                "relative_path": "review_CN.md",
                "sha256": _sha256_bytes(review_bytes),
                "size_bytes": len(review_bytes),
            },
            {
                "relative_path": "summary.json",
                "sha256": _sha256_bytes(summary_bytes),
                "size_bytes": len(summary_bytes),
            },
        ],
        "profile_contract_version": PROFILE_CONTRACT_VERSION,
        "profile_id": PROFILE_ID,
        "run_id": run_id,
    }


def load_verified_stage1_5j_c_launch_time_path_feasibility_root(
    root_path: Path,
    *,
    expected_artifact_kind: str,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Strict J-C domain loader: verify sealed tree, schema, authority seals, review template, and independent raw replay."""
    if RISK_LIVE_TRADING_ENABLED is not False:
        raise Stage1_5JCDiagnosticError("STOP=configs_risk_live_trading_enabled_must_be_false")

    if expected_artifact_kind not in ("validation_only", "production_diagnostic"):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_artifact_kind_mismatch:invalid_expected:{expected_artifact_kind}"
        )

    proj = project_root if project_root is not None else resolve_project_root()
    if _has_symlink_ancestor(
        root_path, stop_at=proj if root_path.is_relative_to(proj) else None
    ) or not root_path.is_dir():
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_root_invalid:not_dir_or_symlink:{root_path}"
        )

    entries = sorted(os.listdir(root_path))
    if entries != ["manifest.json", "review_CN.md", "summary.json"]:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_sealed_tree_violation:{entries}"
        )
    for name in entries:
        fp = root_path / name
        if os.path.islink(fp) or not fp.is_file():
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_sealed_tree_violation:non_regular:{fp}"
            )

    manifest_bytes = (root_path / "manifest.json").read_bytes()
    summary_bytes = (root_path / "summary.json").read_bytes()
    review_bytes = (root_path / "review_CN.md").read_bytes()

    manifest_obj = _parse_canonical_json_bytes(manifest_bytes, "manifest.json")
    summary_obj = _parse_canonical_json_bytes(summary_bytes, "summary.json")

    if (
        not isinstance(manifest_obj, dict)
        or set(manifest_obj.keys()) != MANIFEST_EXACT_KEYS
    ):
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_manifest_keyset_invalid")
    if (
        not isinstance(summary_obj, dict)
        or set(summary_obj.keys()) != SUMMARY_EXACT_KEYS
    ):
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_summary_keyset_invalid")

    if (
        manifest_obj["profile_id"] != PROFILE_ID
        or manifest_obj["profile_contract_version"] != PROFILE_CONTRACT_VERSION
        or summary_obj["profile_id"] != PROFILE_ID
        or summary_obj["profile_contract_version"] != PROFILE_CONTRACT_VERSION
    ):
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_profile_mismatch")

    run_id = str(summary_obj["run_id"])
    validate_run_id_grammar(run_id)
    if manifest_obj["run_id"] != run_id or root_path.name != run_id:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_run_id_mismatch")

    if (
        manifest_obj["artifact_kind"] != expected_artifact_kind
        or summary_obj["artifact_kind"] != expected_artifact_kind
    ):
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_artifact_kind_mismatch:{summary_obj['artifact_kind']}!={expected_artifact_kind}"
        )

    if expected_artifact_kind == "production_diagnostic":
        expected_prod_root = (proj / OUTPUT_PARENT_RELATIVE_PATH / run_id).resolve()
        if root_path.resolve() != expected_prod_root:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_production_root_path_mismatch:{root_path}"
            )

    expected_manifest = build_stage1_5j_c_manifest(
        run_id=run_id,
        artifact_kind=expected_artifact_kind,
        summary_bytes=summary_bytes,
        review_bytes=review_bytes,
    )
    if manifest_obj != expected_manifest:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_manifest_seal_mismatch")

    try:
        review_text = review_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_review_utf8_invalid") from exc
    expected_review = render_stage1_5j_c_review(summary_obj)
    if review_text != expected_review:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_review_render_mismatch")

    # Verify protocol and permissions
    if summary_obj["protocol"] != EXPECTED_PROTOCOL_OBJECT:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_protocol_mismatch")
    perms = summary_obj["permissions"]
    if not isinstance(perms, dict) or set(perms.keys()) != PERMISSIONS_EXACT_KEYS:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_permissions_keyset_invalid")
    for pk, pv in perms.items():
        if pv is not False or type(pv) is not bool:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_permission_not_false:{pk}"
            )

    # Verify authority seals on disk
    auth = summary_obj["authority"]
    if not isinstance(auth, dict) or set(auth.keys()) != AUTHORITY_EXACT_KEYS:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_authority_keyset_invalid")
    for single_key in (
        "design",
        "plan",
        "user_receipt_generation_approval",
        "authorization_release",
        "run_authorization",
    ):
        seal = auth[single_key]
        actual_seal = _make_file_seal(proj, str(seal["relative_path"]))
        if actual_seal != seal:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_authority_seal_mismatch:{single_key}"
            )
    for list_key in ("source_files", "input_files"):
        for seal in auth[list_key]:
            actual_seal = _make_file_seal(proj, str(seal["relative_path"]))
            if actual_seal != seal:
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_authority_seal_mismatch:{list_key}:{seal['relative_path']}"
                )

    # Replay from admitted upstream inputs
    ja_root, ja_summary, jb_child_rows, exp_univ, exp_sel = (
        _load_upstream_ja_and_jb_for_replay(proj)
    )
    ledger_path = proj / LEDGER_RELATIVE_PATH
    replayed_summary = compute_stage1_5j_c_summary_from_admitted_inputs(
        run_id=run_id,
        artifact_kind=expected_artifact_kind,
        authority_obj=auth,
        protocol_obj=summary_obj["protocol"],
        ja_root=ja_root,
        ja_summary=ja_summary,
        jb_child_rows=jb_child_rows,
        ledger_path=ledger_path,
        project_root=proj,
        expected_universe_count=exp_univ,
        expected_selected_count=exp_sel,
    )
    if replayed_summary != summary_obj:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_domain_replay_mismatch")

    return summary_obj


# -----------------------------------------------------------------------------
# Independent Oracles (Zero calls to production parser/reducer/stat helpers)
# -----------------------------------------------------------------------------

ORACLE_PRL_PARENT_ID = "0116dd83010043bd95c37626e2277bbe"
ORACLE_PRL_SYMBOL = "PRLUSDT"


def _oracle_frac_str(f: Fraction) -> str:
    if f.numerator == 0:
        return "0/1"
    return f"{f.numerator}/{f.denominator}"


def _oracle_dates_utc(t0_ms: int, horizon_ms: int) -> list[str]:
    t_end_ms = t0_ms + horizon_ms
    d_cur = datetime.fromtimestamp(t0_ms / 1000.0, tz=timezone.utc).date()
    d_last = datetime.fromtimestamp(t_end_ms / 1000.0, tz=timezone.utc).date()
    res: list[str] = []
    while d_cur <= d_last:
        res.append(d_cur.strftime("%Y-%m-%d"))
        d_cur += timedelta(days=1)
    return res


def _oracle_evaluate_single_child(
    admitted_ja_context: AdmittedJAContext,
    parent_article_id: str,
    symbol: str,
    listing_regime: str,
    jb_row: dict[str, Any],
) -> list[dict[str, Any]]:
    """Independent stdlib-only child evaluator for fixed PRL gap oracle and positive semantic oracle."""
    def _empty_pair(st: str, t0_obj: dict[str, Any] | None = None, entry_obj: dict[str, Any] | None = None, end_obj: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for d_name in ("long", "short"):
            out.append(
                {
                    "direction": d_name,
                    "endpoint": dict(end_obj) if end_obj is not None else None,
                    "entry": dict(entry_obj) if entry_obj is not None else None,
                    "first_touch": "unavailable",
                    "listing_regime": listing_regime,
                    "mae_bps": None,
                    "mae_trade": None,
                    "max_intertrade_gap_ms": None,
                    "mfe_bps": None,
                    "mfe_trade": None,
                    "parent_article_id": parent_article_id,
                    "state": st,
                    "symbol": symbol,
                    "t0": dict(t0_obj) if t0_obj is not None else None,
                    "terminal_bps": None,
                    "touch_trade": None,
                }
            )
        return out

    if jb_row["j_a_parent_state"] != "coverage_complete":
        return _empty_pair("inherited_j_a_parent_gap")
    if jb_row["anchor_state"] != "anchor_found":
        return _empty_pair("anchor_unavailable")

    launch_ms = int(jb_row["symbol_launch_time_ms"])
    anchor_ms = int(jb_row["anchor_time_ms"])
    anchor_price_str = str(jb_row["anchor_price"])
    req_dates = _oracle_dates_utc(anchor_ms, 900_000)

    for d_str in req_dates[1:]:
        k = (parent_article_id, symbol, d_str)
        if (
            k not in admitted_ja_context.package_by_key
            or admitted_ja_context.package_by_key[k]["child_state"]
            != "archive_verified_with_post_launch_rows"
        ):
            # Stream first package to find t0
            pkg0 = admitted_ja_context.package_by_key[(parent_article_id, symbol, req_dates[0])]
            t0_found: dict[str, Any] | None = None
            with open_j_c_verified_package_stream(
                admitted_ja_context,
                pkg0,
                expected_parent_article_id=parent_article_id,
                expected_symbol=symbol,
                expected_utc_date=req_dates[0],
            ) as buf:
                _ = buf.readline(65537)
                r_idx = 0
                while True:
                    b_line = buf.readline(65537)
                    if not b_line:
                        break
                    r_idx += 1
                    cols = next(csv.reader([b_line.decode("utf-8")]))
                    ts_val = int(cols[5])
                    if t0_found is None and ts_val >= launch_ms:
                        t0_found = {
                            "agg_trade_id": int(cols[0]),
                            "physical_row": r_idx,
                            "price": cols[1],
                            "time_ms": ts_val,
                            "utc_date": req_dates[0],
                        }
            return _empty_pair("required_package_unavailable", t0_obj=t0_found)

    t_obs_ms = anchor_ms + 63_000
    t_entry_max_ms = anchor_ms + 64_000
    t_end_min_ms = anchor_ms + 899_000
    t_end_ms = anchor_ms + 900_000

    t0_ref: dict[str, Any] | None = None
    entry_ref: dict[str, Any] | None = None
    end_ref: dict[str, Any] | None = None
    path_records: list[tuple[dict[str, Any], Fraction]] = []
    seq_gap = False
    prev_window_id: int | None = None

    for d_str in req_dates:
        pkg = admitted_ja_context.package_by_key[(parent_article_id, symbol, d_str)]
        with open_j_c_verified_package_stream(
            admitted_ja_context,
            pkg,
            expected_parent_article_id=parent_article_id,
            expected_symbol=symbol,
            expected_utc_date=d_str,
        ) as buf:
            _ = buf.readline(65537)
            r_idx = 0
            while True:
                b_line = buf.readline(65537)
                if not b_line:
                    break
                r_idx += 1
                cols = next(csv.reader([b_line.decode("utf-8")]))
                tid = int(cols[0])
                p_str = cols[1]
                p_frac = Fraction(Decimal(p_str))
                ts = int(cols[5])
                ref = {
                    "agg_trade_id": tid,
                    "physical_row": r_idx,
                    "price": p_str,
                    "time_ms": ts,
                    "utc_date": d_str,
                }
                if t0_ref is None and ts >= launch_ms:
                    if ts != anchor_ms or Decimal(p_str) != Decimal(anchor_price_str):
                        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_oracle_anchor_mismatch")
                    t0_ref = ref
                if t0_ref is not None and ts <= t_end_ms:
                    if prev_window_id is not None and tid != prev_window_id + 1:
                        seq_gap = True
                    prev_window_id = tid
                    if entry_ref is None and t_obs_ms <= ts <= t_entry_max_ms:
                        entry_ref = ref
                    if entry_ref is not None:
                        path_records.append((ref, p_frac))
                        if ts <= t_end_ms:
                            end_ref = ref

    if entry_ref is None:
        return _empty_pair("entry_unavailable", t0_obj=t0_ref)
    if end_ref is None or int(end_ref["time_ms"]) < t_end_min_ms:
        return _empty_pair("endpoint_unavailable", t0_obj=t0_ref, entry_obj=entry_ref)
    if seq_gap:
        return _empty_pair(
            "sequence_gap", t0_obj=t0_ref, entry_obj=entry_ref, end_obj=end_ref
        )

    pe_frac = path_records[0][1]
    max_gap = 0
    for idx in range(1, len(path_records)):
        dt = int(path_records[idx][0]["time_ms"]) - int(path_records[idx - 1][0]["time_ms"])
        if dt > max_gap:
            max_gap = dt

    results: list[dict[str, Any]] = []
    for d_name in ("long", "short"):
        mfe_val: Fraction | None = None
        mfe_tr: dict[str, Any] | None = None
        mae_val: Fraction | None = None
        mae_tr: dict[str, Any] | None = None
        f_touch = "neither"
        t_tr: dict[str, Any] | None = None
        term_val: Fraction | None = None

        for ref, p_frac in path_records:
            if d_name == "long":
                bps = Fraction(10000, 1) * (p_frac / pe_frac - Fraction(1, 1))
            else:
                bps = Fraction(10000, 1) * (Fraction(1, 1) - p_frac / pe_frac)
            term_val = bps
            if mfe_val is None or bps > mfe_val:
                mfe_val = bps
                mfe_tr = ref
            if mae_val is None or bps < mae_val:
                mae_val = bps
                mae_tr = ref
            if f_touch == "neither":
                if bps >= Fraction(3000, 1):
                    f_touch = "target"
                    t_tr = ref
                elif bps <= Fraction(-200, 1):
                    f_touch = "risk"
                    t_tr = ref

        assert mfe_val is not None and mae_val is not None and term_val is not None
        results.append(
            {
                "direction": d_name,
                "endpoint": dict(end_ref),
                "entry": dict(entry_ref),
                "first_touch": f_touch,
                "listing_regime": listing_regime,
                "mae_bps": _oracle_frac_str(mae_val),
                "mae_trade": dict(mae_tr) if mae_tr is not None else None,
                "max_intertrade_gap_ms": max_gap,
                "mfe_bps": _oracle_frac_str(mfe_val),
                "mfe_trade": dict(mfe_tr) if mfe_tr is not None else None,
                "parent_article_id": parent_article_id,
                "state": "complete",
                "symbol": symbol,
                "t0": dict(t0_ref) if t0_ref is not None else None,
                "terminal_bps": _oracle_frac_str(term_val),
                "touch_trade": dict(t_tr) if t_tr is not None else None,
            }
        )
    return results


def run_prl_fixed_gap_oracle(
    *,
    admitted_ja_context: AdmittedJAContext,
    jb_child_rows: list[dict[str, Any]],
    summary_data: dict[str, Any],
) -> dict[str, Any]:
    """Fixed PRLUSDT (Parent 0116dd83010043bd95c37626e2277bbe) gap oracle."""
    jb_matches = [
        r
        for r in jb_child_rows
        if r["source_article_id"] == ORACLE_PRL_PARENT_ID
        and r["symbol"] == ORACLE_PRL_SYMBOL
    ]
    if len(jb_matches) != 1:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_prl_oracle_jb_row_missing")
    jb_row = jb_matches[0]

    u_matches = [
        u
        for u in summary_data["universe_rows"]
        if u["parent_article_id"] == ORACLE_PRL_PARENT_ID
        and u["symbol"] == ORACLE_PRL_SYMBOL
    ]
    if len(u_matches) != 1:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_prl_oracle_universe_row_missing")
    reg = str(u_matches[0]["listing_regime"])

    oracle_pair = _oracle_evaluate_single_child(
        admitted_ja_context=admitted_ja_context,
        parent_article_id=ORACLE_PRL_PARENT_ID,
        symbol=ORACLE_PRL_SYMBOL,
        listing_regime=reg,
        jb_row=jb_row,
    )
    summary_pair = sorted(
        [
            c
            for c in summary_data["child_rows"]
            if c["parent_article_id"] == ORACLE_PRL_PARENT_ID
            and c["symbol"] == ORACLE_PRL_SYMBOL
        ],
        key=lambda x: str(x["direction"]),
    )
    if oracle_pair != summary_pair:
        raise Stage1_5JCDiagnosticError("STOP=stage1_5j_c_prl_oracle_parity_mismatch")

    return {
        "observed_state": oracle_pair[0]["state"],
        "parent_article_id": ORACLE_PRL_PARENT_ID,
        "status": "passed",
        "symbol": ORACLE_PRL_SYMBOL,
    }


def run_positive_semantic_oracle(
    *,
    admitted_ja_context: AdmittedJAContext,
    jb_child_rows: list[dict[str, Any]],
    summary_data: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic lexical (parent_article_id, symbol) first-complete positive semantic oracle."""
    jb_by_key = {
        (str(r["source_article_id"]), str(r["symbol"])): r for r in jb_child_rows
    }
    in_scope_universe = sorted(
        [u for u in summary_data["universe_rows"] if u["in_scope"] is True],
        key=lambda u: (str(u["parent_article_id"]), str(u["symbol"])),
    )

    selected_pair: list[dict[str, Any]] | None = None
    selected_key: tuple[str, str] | None = None

    for u in in_scope_universe:
        pid = str(u["parent_article_id"])
        sym = str(u["symbol"])
        reg = str(u["listing_regime"])
        pair = _oracle_evaluate_single_child(
            admitted_ja_context=admitted_ja_context,
            parent_article_id=pid,
            symbol=sym,
            listing_regime=reg,
            jb_row=jb_by_key[(pid, sym)],
        )
        if pair[0]["state"] == "complete" and pair[1]["state"] == "complete":
            selected_pair = pair
            selected_key = (pid, sym)
            break

    if selected_pair is None or selected_key is None:
        return {
            "selected_parent_article_id": None,
            "selected_symbol": None,
            "status": "positive_semantic_evidence_unavailable",
        }

    pid, sym = selected_key
    summary_pair = sorted(
        [
            c
            for c in summary_data["child_rows"]
            if c["parent_article_id"] == pid and c["symbol"] == sym
        ],
        key=lambda x: str(x["direction"]),
    )
    if selected_pair != summary_pair:
        raise Stage1_5JCDiagnosticError(
            f"STOP=stage1_5j_c_positive_oracle_child_mismatch:{pid}:{sym}"
        )

    # Also verify parent-level projection for this selected child's parent when single-symbol complete
    for dir_row in selected_pair:
        d_name = str(dir_row["direction"])
        reg = str(dir_row["listing_regime"])
        p_matches = [
            p
            for p in summary_data["parent_rows"]
            if p["parent_article_id"] == pid
            and p["listing_regime"] == reg
            and p["direction"] == d_name
        ]
        if len(p_matches) != 1 or sym not in p_matches[0]["symbols"]:
            raise Stage1_5JCDiagnosticError(
                f"STOP=stage1_5j_c_positive_oracle_parent_mismatch:{pid}:{sym}"
            )
        if p_matches[0]["state"] == "complete" and p_matches[0]["symbols"] == [sym]:
            if (
                p_matches[0]["mfe_bps"] != dir_row["mfe_bps"]
                or p_matches[0]["mae_bps"] != dir_row["mae_bps"]
                or p_matches[0]["terminal_bps"] != dir_row["terminal_bps"]
            ):
                raise Stage1_5JCDiagnosticError(
                    f"STOP=stage1_5j_c_positive_oracle_parent_metric_mismatch:{pid}:{sym}"
                )

    return {
        "selected_parent_article_id": pid,
        "selected_symbol": sym,
        "status": "passed",
    }

