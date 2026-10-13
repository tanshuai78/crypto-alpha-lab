"""Stage 1.5J-B Historical aggTrades Launch-Anchor Price-Response Exploratory Research Core Module.

Implements:
1. Authority bundle verification and immutable input gates.
2. Upstream Stage 1.5J-A replacement root admission and Rule 17 v2 closure verification.
3. Resource caps and bounded streaming ZIP/CSV extraction.
4. Launch-anchor identification and fixed-horizon price-response sampling.
5. Child outcome calculation, parent median aggregation, distribution and concentration statistics.
6. Atomic receipt serialization, flock publication, strict loader, and Markdown rendering.
"""

from __future__ import annotations

import fcntl
import hashlib
import importlib
import json
import math
import os
import re
import sys
import zipfile
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Any

from configs.base import RISK_LIVE_TRADING_ENABLED

# -----------------------------------------------------------------------------
# Constants & Authority Identifiers
# -----------------------------------------------------------------------------

PLAN_SHA = "ec5fbc3beeafd47ec42cdf12481751f41424fe3351a6c14845ebc0e5d5a8a319"
TASK0_AUTHORITY_DIR = Path(".git/plan-execution/stage1_5j_b") / PLAN_SHA

STAGE_CONFIG_RELATIVE_PATH = "configs/stage1_5j_b_historical_aggtrades_launch_response.py"
STAGE_CONFIG_SOURCE_SHA256 = "771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4"
STAGE_CONFIG_BYTE_COUNT = 565

SCHEMA_VERSION = "stage1_5j_b_historical_aggtrades_launch_response_v1"
RUN_ID_REGEX = re.compile(r"^stage1_5j_b_historical_aggtrades_launch_response_[0-9]{8}T[0-9]{6}Z$")
OUTPUT_PARENT_RELATIVE = "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response"

J_B_PARENT_DESIGN_PATH = "docs/designs/2026-10-07-external-signal-shadow-lab-stage1-5j-b-historical-aggtrades-launch-anchor-price-response-exploratory-design_CN.md"
J_B_PARENT_DESIGN_SHA256 = "ce3ce71fae455d1a623269965d23251870f5e638e849cb3fb13f08751360165b"

J_B_REBIND_DELTA_PATH = "docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-replacement-receipt-rebind-design-delta_CN.md"
J_B_REBIND_DELTA_SHA256 = "0f131b044124646ec0a3bd5394fa085d1e08f5d0724790d7ef39bbfb7a23100c"

J_B_RECEIPT_SCHEMA_AUTHORITY_PATH = "docs/designs/2026-10-11-external-signal-shadow-lab-stage1-5j-b-receipt-schema-authority-clarification-design-delta_CN.md"
J_B_RECEIPT_SCHEMA_AUTHORITY_SHA256 = "f108c5c3004a2aac0067abc27046f5411f66264cdb7e128333f278ec1cd23e25"

J_B_COMPATIBILITY_DOMAIN_DELTA_PATH = "docs/designs/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-rule17-config-authority-design-delta_CN.md"
J_B_COMPATIBILITY_DOMAIN_DELTA_SHA256 = "66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f"

GOVERNANCE_PROFILE_DELTA_PATH = "docs/designs/2026-10-11-governance-stage1-5j-b-receipt-rule17-profile-design-delta_CN.md"
GOVERNANCE_PROFILE_DELTA_SHA256 = "a692a888e1a9ae6b66379045fc031c6075eb72ff99fc30d140dd671caaa1153b"

J_A_CANONICAL_ROOT_RELATIVE = "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
J_A_CANONICAL_RUN_ID = "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
J_A_CANONICAL_CORE_PATH = "src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py"
J_A_CANONICAL_CORE_SHA256 = "250fdb9fd16f029905811e79d330f77d5b75d856840d559cb604ef3c7c2e1e18"
J_B_CANONICAL_CORE_PATH = "src/research/external_signal_shadow/stage1_5j_b_historical_aggtrades_launch_response.py"

J_A_FOUR_ARTIFACTS_SHA256 = {
    "manifest.json": "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf",
    "request_journal.jsonl": "b00b7d4c6da98ba4901ac3a5e0f3b1b72afa245d288ed74bf6d21c03a90f28aa",
    "review_CN.md": "1405184e109cbc8efcf3356ebedc6904ec0384e138653f026a63042fcf42d152",
    "summary.json": "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b",
}

J_A_GOVERNANCE_CLOSURE_EVIDENCE_PATH = ".git/plan-execution/governance_artifact_schema/ba362f2480c7872d39eede9254744d6e99216aa73134777658f9f81f05ba7881/evidence/v2_receipt_closure_evidence.json"
J_A_GOVERNANCE_CLOSURE_EVIDENCE_SHA256 = "c0810b95dc94c740dbc41d55ce01d51d1bd7a09e382b292e156d2522d621e68b"

REQUIRED_CSV_HEADER = [
    "agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"
]

CANONICAL_AUTHORITY_FLAGS = {
    "alpha_claim_allowed": False,
    "broker_routing_allowed": False,
    "capital_commitment_allowed": False,
    "discretionary_override_allowed": False,
    "execution_engine_allowed": False,
    "execution_feasibility_claim_allowed": False,
    "live_trading_allowed": False,
    "network_access_allowed": False,
    "paper_trading_allowed": False,
    "position_sizing_allowed": False,
    "realtime_telemetry_allowed": False,
    "trade_intent_allowed": False,
}

CANONICAL_RESEARCH_STATUS = {
    "alpha_evidence_status": "evidence_insufficient",
    "capital_survival_claim": "not_evaluated",
    "economic_edge_claim": "not_evaluated",
    "execution_feasibility_claim": "not_evaluated",
    "live_permission_claim": False,
    "phenomenon_claim": "not_evaluated",
    "research_mode": "exploratory_descriptive_only",
    "statistical_edge_claim": "not_evaluated",
}


CHILD_ROW_REQUIRED_KEYS = {
    "anchor_delay_ms",
    "anchor_price",
    "anchor_state",
    "anchor_time_ms",
    "j_a_child_state",
    "j_a_parent_state",
    "required_archive_dates_by_horizon",
    "source_article_id",
    "symbol",
    "symbol_launch_time_ms",
}

LEGAL_ANCHOR_STATES = {
    "evidence_gap",
    "anchor_found",
    "anchor_unavailable_inherited_j_a_parent_gap",
    "anchor_unavailable_delay_exceeded",
}

CHILD_HORIZON_ROW_REQUIRED_KEYS = {
    "child_horizon_state",
    "gross_return_bps",
    "horizon_ms",
    "horizon_offset_ms",
    "horizon_price",
    "horizon_selected_time_ms",
    "horizon_target_time_ms",
    "missing_reason",
    "sampled_max_excursion_bps",
    "sampled_min_excursion_bps",
    "source_article_id",
    "symbol",
    "trade_count",
}

LEGAL_CHILD_HORIZON_STATES = {
    "child_horizon_complete",
    "child_horizon_evidence_gap",
}

LEGAL_MISSING_REASONS = {
    "inherited_j_a_parent_gap",
    "evidence_gap_missing_launch_time",
    "evidence_gap_anchor_delay",
    "evidence_gap_missing_required_archive_package",
    "evidence_gap_missing_horizon_trade",
}

PARENT_HORIZON_ROW_REQUIRED_KEYS = {
    "failed_child_reasons",
    "horizon_ms",
    "parent_gross_return_bps",
    "parent_horizon_state",
    "parent_sampled_max_excursion_bps",
    "parent_sampled_min_excursion_bps",
    "source_article_id",
    "source_parent_state",
}

LEGAL_PARENT_HORIZON_STATES = {
    "parent_horizon_complete",
    "parent_horizon_evidence_gap",
}

SUMMARY_REQUIRED_KEYS = {
    "analysis_state",
    "authority_flags",
    "authority_packet",
    "child_horizon_rows",
    "child_rows",
    "coverage_counts",
    "decision",
    "j_a_input",
    "parent_horizon_rows",
    "research_status",
    "run_id",
    "schema_version",
}

COVERAGE_COUNTS_REQUIRED_KEYS = {
    "j_a_parent_coverage_complete_count",
    "j_a_parent_coverage_gap_count",
    "j_a_target_parent_count",
    "n_child_horizon_complete_by_horizon",
    "n_child_horizon_gap_by_horizon",
    "n_parent_horizon_complete_by_horizon",
    "n_parent_horizon_gap_by_horizon",
    "n_parent_total",
    "n_parent_with_j_a_gap",
    "parent_distribution_by_horizon",
}

PARENT_DIST_REQUIRED_KEYS = {
    "max",
    "mean",
    "median",
    "min",
    "n_complete_parent",
    "p10",
    "p25",
    "p50",
    "p75",
    "p90",
    "top_1_abs_return_contribution",
    "top_1_parent_ids",
    "top_3_abs_return_contribution",
    "top_3_parent_ids",
}

LEGAL_J_A_PARENT_STATES = {
    "coverage_complete",
    "coverage_evidence_gap_archive",
    "coverage_evidence_gap_detail",
    "coverage_evidence_gap_no_in_scope_usdt_child",
}

LEGAL_J_A_CHILD_STATES = {
    "j_a_child_coverage_complete",
    "j_a_child_coverage_gap",
}

RECEIPT_AUTH_ORDERED_KEYS: tuple[str, ...] = (
    "APPROVED_J_B_DESIGN_SHA256",
    "APPROVED_J_B_PLAN_SHA256",
    "AUTHORIZED_RUN_ID",
    "AUDITED_J_B_CORE_SHA256",
    "AUDITED_J_B_CLI_SHA256",
    "AUDITED_CONFIG_SHA256",
    "J_A_MANIFEST_SHA256",
    "NETWORK_ALLOWED",
)
RECEIPT_AUTH_REQUIRED_KEYS = frozenset(RECEIPT_AUTH_ORDERED_KEYS)


class Stage1_5JBDiagnosticError(Exception):
    """Raised when an explicit invariant fails in Stage 1.5J-B."""
    pass


# -----------------------------------------------------------------------------
# Helpers: File & Hash Utilities
# -----------------------------------------------------------------------------

def _resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _verify_canonical_json(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def format_canonical_decimal(d: Decimal) -> str:
    """Format Decimal without scientific notation or redundant zeros; zero is '0'."""
    if not d.is_finite():
        raise Stage1_5JBDiagnosticError("format_canonical_decimal: non-finite decimal")
    if d == Decimal(0):
        return "0"
    sign, digits, exp = d.as_tuple()
    if exp >= 0:
        s = "".join(str(digit) for digit in digits) + ("0" * exp)
    else:
        abs_exp = -exp
        if len(digits) <= abs_exp:
            s = "0." + ("0" * (abs_exp - len(digits))) + "".join(str(digit) for digit in digits)
        else:
            s = "".join(str(digit) for digit in digits[:-abs_exp]) + "." + "".join(str(digit) for digit in digits[-abs_exp:])
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if sign:
        s = "-" + s
    return s if s != "-0" else "0"


def format_canonical_bps(d: Decimal) -> str:
    """Quantize to 8 decimal places with ROUND_HALF_EVEN and format canonically."""
    quantized = d.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
    return format_canonical_decimal(quantized)


# -----------------------------------------------------------------------------
# 0. Stage-Local Config Verification & Constants
# -----------------------------------------------------------------------------

STAGE_CONFIG_PATH = _resolve_project_root() / STAGE_CONFIG_RELATIVE_PATH


def _verify_stage_config(stage_config_path: Path | None = None) -> dict[str, Any]:
    """Verify Stage 1.5J-B stage-local configuration module in frozen sequence."""
    cfg_path = stage_config_path if stage_config_path is not None else STAGE_CONFIG_PATH

    # 1. Resolve canonical path & check symlinks
    if cfg_path.is_symlink():
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_config_authority_mismatch:symlink_detected")
    if not cfg_path.is_file():
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_config_authority_mismatch:file_not_found")

    raw_bytes = cfg_path.read_bytes()
    if len(raw_bytes) != STAGE_CONFIG_BYTE_COUNT:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_config_authority_mismatch:byte_count_mismatch:{len(raw_bytes)}")
    if _sha256_bytes(raw_bytes) != STAGE_CONFIG_SOURCE_SHA256:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_config_authority_mismatch:pre_sha_mismatch")

    # Invalidate caches & evict exact module
    importlib.invalidate_caches()
    module_name = "configs.stage1_5j_b_historical_aggtrades_launch_response"
    sys.modules.pop(module_name, None)

    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_config_authority_mismatch:import_failed:{e}") from e

    # Check origin
    mod_file = getattr(mod, "__file__", None)
    if mod_file is None or Path(mod_file).resolve() != cfg_path.resolve():
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_config_authority_mismatch:origin_mismatch")

    # Check exact public names and values
    expected: dict[str, Any] = {
        "EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS": 300_000,
        "EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS": (300_000, 3_600_000, 14_400_000),
        "EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS": 60_000,
        "EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES": 268_435_456,
        "EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES": 536_870_912,
        "EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO": 64,
        "EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES": 65_536,
        "EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES": 67_108_864,
        "EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES": 1_073_741_824,
    }
    public_names = {k for k in dir(mod) if not k.startswith("_")}
    if public_names != set(expected.keys()):
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_config_authority_mismatch:public_names_mismatch")

    verified = {}
    for k, exp_val in expected.items():
        val = getattr(mod, k)
        if isinstance(exp_val, tuple):
            if not isinstance(val, tuple) or not all(type(x) is int for x in val) or val != exp_val:
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_config_authority_mismatch:value_mismatch:{k}")
        else:
            if type(val) is not int or val != exp_val:
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_config_authority_mismatch:value_mismatch:{k}")
        verified[k] = val

    # Recompute post-import bytes and SHA
    post_bytes = cfg_path.read_bytes()
    if len(post_bytes) != STAGE_CONFIG_BYTE_COUNT or _sha256_bytes(post_bytes) != STAGE_CONFIG_SOURCE_SHA256:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_config_authority_mismatch:post_sha_mismatch")

    if RISK_LIVE_TRADING_ENABLED is not False:
        raise Stage1_5JBDiagnosticError("STOP=configs_risk_live_trading_enabled_must_be_false")

    return verified


_VERIFIED_STAGE_CONFIG = _verify_stage_config()
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS = _VERIFIED_STAGE_CONFIG["EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS"]
EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS = _VERIFIED_STAGE_CONFIG["EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS"]
EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS = _VERIFIED_STAGE_CONFIG["EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS"]
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES = _VERIFIED_STAGE_CONFIG["EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES"]
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES = _VERIFIED_STAGE_CONFIG["EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES"]
EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO = _VERIFIED_STAGE_CONFIG["EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO"]
EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES = _VERIFIED_STAGE_CONFIG["EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES"]
EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES = _VERIFIED_STAGE_CONFIG["EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES"]
EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES = _VERIFIED_STAGE_CONFIG["EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES"]


# -----------------------------------------------------------------------------
# 1. Task 0 Execution Authority Verification
# -----------------------------------------------------------------------------


def verify_execution_authority() -> dict[str, Any]:
    """Verify Task 0 canonical implementation authority bundle."""
    proj = _resolve_project_root()
    bundle_dir = proj / TASK0_AUTHORITY_DIR
    if not bundle_dir.is_dir():
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_execution_authority_missing:{bundle_dir}")

    # 1. Check implementation_authorization.txt
    auth_file = bundle_dir / "implementation_authorization.txt"
    if not auth_file.is_file():
        raise Stage1_5JBDiagnosticError("STOP=implementation_authorization_missing")

    lines = auth_file.read_bytes().split(b"\n")
    if len(lines) != 3 or lines[2] != b"":
        raise Stage1_5JBDiagnosticError("STOP=implementation_authorization_grammar_invalid")

    line1 = lines[0].decode("utf-8")
    line2 = lines[1].decode("utf-8")
    if not line1.startswith("我批准实施 Plan：docs/plans/2026-10-12-external-signal-shadow-lab-stage1-5j-b-historical-receipt-compatibility-domain-implementation-plan_CN.md"):
        raise Stage1_5JBDiagnosticError("STOP=implementation_authorization_grammar_invalid:plan_path")
    if f"SHA-256: {PLAN_SHA}" not in line1:
        raise Stage1_5JBDiagnosticError("STOP=implementation_authorization_grammar_invalid:plan_sha_mismatch")
    if line2 != "允许 implementation；不允许 commit、push、deployment、SSH 或 runtime action。":
        raise Stage1_5JBDiagnosticError("STOP=implementation_authorization_grammar_invalid:permissions_clause")

    # Verify sidecar
    auth_sidecar = bundle_dir / "implementation_authorization.txt.sha256"
    if not auth_sidecar.is_file():
        raise Stage1_5JBDiagnosticError("STOP=implementation_authorization_sidecar_missing")
    expected_sidecar_line = f"{_sha256_file(auth_file)}  implementation_authorization.txt\n"
    if auth_sidecar.read_text(encoding="utf-8") != expected_sidecar_line:
        raise Stage1_5JBDiagnosticError("STOP=implementation_authorization_sidecar_mismatch")

    # 2. Check domain_design_authorization.txt
    domain_auth_file = bundle_dir / "domain_design_authorization.txt"
    if not domain_auth_file.is_file():
        raise Stage1_5JBDiagnosticError("STOP=domain_design_authorization_missing")
    d_lines = domain_auth_file.read_bytes().split(b"\n")
    if len(d_lines) != 3 or d_lines[2] != b"":
        raise Stage1_5JBDiagnosticError("STOP=domain_design_authorization_grammar_invalid")
    if "66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f" not in d_lines[0].decode("utf-8"):
        raise Stage1_5JBDiagnosticError("STOP=domain_design_authorization_sha_mismatch")
    d_sidecar = bundle_dir / "domain_design_authorization.txt.sha256"
    if not d_sidecar.is_file() or d_sidecar.read_text(encoding="utf-8") != f"{_sha256_file(domain_auth_file)}  domain_design_authorization.txt\n":
        raise Stage1_5JBDiagnosticError("STOP=domain_design_authorization_sidecar_mismatch")

    # 3. Check governance_design_authorization.txt
    gov_auth_file = bundle_dir / "governance_design_authorization.txt"
    if not gov_auth_file.is_file():
        raise Stage1_5JBDiagnosticError("STOP=governance_design_authorization_missing")
    g_lines = gov_auth_file.read_bytes().split(b"\n")
    if len(g_lines) != 3 or g_lines[2] != b"":
        raise Stage1_5JBDiagnosticError("STOP=governance_design_authorization_grammar_invalid")
    if "8bdfe8de98c43e23de5b03bf53fa9cc1c9a8e6e40da02cc3ef83c8b3615b1454" not in g_lines[0].decode("utf-8"):
        raise Stage1_5JBDiagnosticError("STOP=governance_design_authorization_sha_mismatch")
    g_sidecar = bundle_dir / "governance_design_authorization.txt.sha256"
    if not g_sidecar.is_file() or g_sidecar.read_text(encoding="utf-8") != f"{_sha256_file(gov_auth_file)}  governance_design_authorization.txt\n":
        raise Stage1_5JBDiagnosticError("STOP=governance_design_authorization_sidecar_mismatch")

    # 4. Check execution_authority.json
    exec_auth_file = bundle_dir / "execution_authority.json"
    if not exec_auth_file.is_file():
        raise Stage1_5JBDiagnosticError("STOP=execution_authority_json_missing")

    exec_auth_sidecar = bundle_dir / "execution_authority.json.sha256"
    if not exec_auth_sidecar.is_file():
        raise Stage1_5JBDiagnosticError("STOP=execution_authority_json_sidecar_missing")
    if exec_auth_sidecar.read_text(encoding="utf-8") != f"{_sha256_file(exec_auth_file)}  execution_authority.json\n":
        raise Stage1_5JBDiagnosticError("STOP=execution_authority_json_sidecar_mismatch")

    auth_data = json.loads(exec_auth_file.read_text(encoding="utf-8"))
    if auth_data.get("schema_version") != "stage1_5j_b_execution_authority_v2":
        raise Stage1_5JBDiagnosticError("STOP=execution_authority_schema_version_invalid")

    if auth_data.get("source_label") != "received_external_handoff":
        raise Stage1_5JBDiagnosticError("STOP=execution_authority_source_label_invalid")

    if auth_data.get("base_sha") != "d15ca4e0da75a61553ca1d5983249d85a4512bb5":
        raise Stage1_5JBDiagnosticError("STOP=execution_authority_base_sha_mismatch")

    if auth_data.get("approved_plan", {}).get("sha256") != PLAN_SHA:
        raise Stage1_5JBDiagnosticError("STOP=execution_authority_plan_sha_mismatch")

    if auth_data.get("risk_live_trading_enabled") is not False:
        raise Stage1_5JBDiagnosticError("STOP=execution_authority_risk_live_trading_must_be_false")

    if RISK_LIVE_TRADING_ENABLED is not False:
        raise Stage1_5JBDiagnosticError("STOP=configs_risk_live_trading_enabled_must_be_false")

    return auth_data


# -----------------------------------------------------------------------------
# 2. Upstream Stage 1.5J-A Root Admission
# -----------------------------------------------------------------------------

def admit_upstream_j_a_root(root_path: Path) -> dict[str, Any]:
    """Admit Stage 1.5J-A replacement root in frozen order."""
    proj = _resolve_project_root()
    canonical_root = proj / J_A_CANONICAL_ROOT_RELATIVE

    # 1. Containment and symlink check
    resolved_root = root_path.resolve()
    resolved_proj = proj.resolve()
    if not str(resolved_root).startswith(str(resolved_proj)):
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_upstream_authority_mismatch:root_escape:{root_path}")

    # Check symlinks in root path components
    cur = root_path
    while cur != proj and cur != cur.parent:
        if cur.is_symlink():
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_upstream_authority_mismatch:symlink_detected:{cur}")
        cur = cur.parent

    if resolved_root != canonical_root.resolve():
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_upstream_authority_mismatch:non_canonical_root:{root_path}")

    # 2. Governance closure evidence check
    evidence_file = proj / J_A_GOVERNANCE_CLOSURE_EVIDENCE_PATH
    if not evidence_file.is_file():
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_governance_evidence_invalid:file_missing")
    if _sha256_file(evidence_file) != J_A_GOVERNANCE_CLOSURE_EVIDENCE_SHA256:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_governance_evidence_invalid:sha_mismatch")

    ev_sidecar = proj / f"{J_A_GOVERNANCE_CLOSURE_EVIDENCE_PATH}.sha256"
    if not ev_sidecar.is_file():
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_governance_evidence_invalid:sidecar_missing")
    if ev_sidecar.read_text(encoding="utf-8").strip().split()[0] != J_A_GOVERNANCE_CLOSURE_EVIDENCE_SHA256:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_governance_evidence_invalid:sidecar_sha_mismatch")

    ev_data = json.loads(evidence_file.read_text(encoding="utf-8"))
    if ev_data.get("profile_id") != "stage1_5j_a_receipt_v2" or ev_data.get("profile_contract_version") != 2:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_governance_evidence_invalid:profile_mismatch")
    if ev_data.get("governance_rule17_v2_positive") is not True:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_governance_evidence_invalid:not_positive")

    # 3. J-A core source SHA check before import
    core_file = proj / J_A_CANONICAL_CORE_PATH
    if not core_file.is_file():
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_authority_mismatch:core_missing")
    if _sha256_file(core_file) != J_A_CANONICAL_CORE_SHA256:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_authority_mismatch:core_sha_mismatch")

    # 4. Import exact module and verify import origin
    mod_name = "src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory"
    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_upstream_authority_mismatch:import_failed:{e}")

    mod_file = getattr(mod, "__file__", None)
    mod_origin = getattr(getattr(mod, "__spec__", None), "origin", None)
    if not mod_file or Path(mod_file).resolve() != core_file.resolve():
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_upstream_authority_mismatch:import_origin_file_mismatch:{mod_file}")
    if not mod_origin or Path(mod_origin).resolve() != core_file.resolve():
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_upstream_authority_mismatch:import_origin_spec_mismatch:{mod_origin}")

    # Re-verify core SHA after import
    if _sha256_file(core_file) != J_A_CANONICAL_CORE_SHA256:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_authority_mismatch:post_import_core_sha_mismatch")

    # 5. Call public strict loader
    loader_func = getattr(mod, "load_verified_stage1_5j_a_historical_archive_coverage_root", None)
    if not callable(loader_func):
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_authority_mismatch:loader_symbol_missing")

    j_a_res = loader_func(root_path)

    # 6. Verify four artifact hashes
    for art_name, expected_sha in J_A_FOUR_ARTIFACTS_SHA256.items():
        art_path = root_path / art_name
        if not art_path.is_file():
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_upstream_authority_mismatch:artifact_missing:{art_name}")
        if _sha256_file(art_path) != expected_sha:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_upstream_authority_mismatch:artifact_sha_mismatch:{art_name}")

    # 7. Verify state, decision, and 9 projections
    if j_a_res.get("run_id") != "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z":
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_authority_mismatch:run_id_mismatch")
    if j_a_res.get("analysis_state") != "coverage_inventory_evidence_gap":
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_authority_mismatch:analysis_state_mismatch")
    if j_a_res.get("decision") != "stage1_5j_a_historical_archive_coverage_evidence_gap_published":
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_upstream_authority_mismatch:decision_mismatch")

    cov = j_a_res.get("coverage_inventory", {})
    expected_projections = {
        "catalog_denominator_count": 335,
        "target_parent_count": 131,
        "resolved_parent_count": 125,
        "parent_coverage_complete_count": 120,
        "parent_coverage_gap_count": 11,
        "in_scope_usdt_child_count": 281,
        "child_coverage_complete_count": 280,
        "child_coverage_gap_count": 1,
        "out_of_scope_child_count": 5,
    }
    for field, expected_val in expected_projections.items():
        if cov.get(field) != expected_val:
            raise Stage1_5JBDiagnosticError(
                f"STOP=stage1_5j_b_upstream_projection_mismatch:{field}:expected={expected_val}:observed={cov.get(field)}"
            )

    return j_a_res


# -----------------------------------------------------------------------------
# 3. Resource Caps and ZIP Archive Validation
# -----------------------------------------------------------------------------

def validate_zip_archive_package(
    zip_path: Path,
    max_zip_bytes: int = EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES,
    max_uncompressed_bytes: int = EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
    max_ratio: int = EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO,
) -> bool:
    """Validate ZIP package meets resource caps before opening or streaming."""
    if not zip_path.is_file():
        return False
    size = zip_path.stat().st_size
    if size > max_zip_bytes or size <= 0:
        return False

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            infolist = zf.infolist()
            if len(infolist) != 1:
                return False
            info = infolist[0]
            if not info.filename.endswith(".csv"):
                return False
            if info.file_size > max_uncompressed_bytes or info.file_size <= 0:
                return False
            if info.compress_size > 0:
                ratio = info.file_size / info.compress_size
                if ratio > max_ratio:
                    return False
    except Exception:
        return False

    return True


def validate_aggtrades_csv_header(header: list[str]) -> bool:
    """Validate that CSV header matches REQUIRED_CSV_HEADER exactly."""
    return header == REQUIRED_CSV_HEADER


# -----------------------------------------------------------------------------
# 4. Deterministic Pricing, Horizons, and Reducer Algorithms
# -----------------------------------------------------------------------------

def compute_required_j_b_dates(anchor_time_ms: int, horizon_ms: int) -> list[str]:
    """Compute sorted list of YYYY-MM-DD UTC dates intersecting [anchor_time_ms, anchor_time_ms + horizon_ms]."""
    start_sec = anchor_time_ms // 1000
    end_sec = (anchor_time_ms + horizon_ms) // 1000

    from datetime import datetime, timedelta, timezone
    start_dt = datetime.fromtimestamp(start_sec, tz=timezone.utc).date()
    end_dt = datetime.fromtimestamp(end_sec, tz=timezone.utc).date()

    cur = start_dt
    dates = []
    while cur <= end_dt:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return sorted(dates)


def select_launch_anchor_trade(
    trades: list[dict[str, Any]],
    symbol_launch_time_ms: int,
    max_delay_ms: int = EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS,
) -> dict[str, Any] | None:
    """Select the first physical trade with transact_time >= symbol_launch_time_ms within max_delay_ms."""
    for t in trades:
        ts = t["transact_time"]
        if ts >= symbol_launch_time_ms:
            if ts - symbol_launch_time_ms <= max_delay_ms:
                return t
            return None  # Exceeded delay limit
    return None


def select_horizon_trade(
    trades: list[dict[str, Any]],
    target_time_ms: int,
    lookback_ms: int = EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS,
) -> dict[str, Any] | None:
    """Select the last physical trade in [target_time_ms - lookback_ms, target_time_ms]."""
    start_window = target_time_ms - lookback_ms
    candidate = None
    for t in trades:
        ts = t["transact_time"]
        if start_window <= ts <= target_time_ms:
            # Later row in physical order replaces earlier candidate
            candidate = t
        elif ts > target_time_ms:
            break
    return candidate


def calculate_child_horizon_outcomes(
    anchor_price: Decimal,
    horizon_price: Decimal,
    sampled_min_price: Decimal,
    sampled_max_price: Decimal,
    horizon_selected_time_ms: int,
    target_time_ms: int,
) -> dict[str, Any]:
    """Calculate gross return and sampled min/max excursions in bps."""
    bps_factor = Decimal(10000)
    gross_return = bps_factor * (horizon_price / anchor_price - Decimal(1))
    min_excursion = bps_factor * (sampled_min_price / anchor_price - Decimal(1))
    max_excursion = bps_factor * (sampled_max_price / anchor_price - Decimal(1))
    offset_ms = horizon_selected_time_ms - target_time_ms

    return {
        "gross_return_bps": format_canonical_bps(gross_return),
        "sampled_min_excursion_bps": format_canonical_bps(min_excursion),
        "sampled_max_excursion_bps": format_canonical_bps(max_excursion),
        "horizon_offset_ms": offset_ms,
    }


def aggregate_parent_horizon_outcomes(child_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate complete child outcomes into parent horizon outcome using simple median."""
    if not child_rows:
        return {
            "parent_gross_return_bps": "0",
            "parent_sampled_min_excursion_bps": "0",
            "parent_sampled_max_excursion_bps": "0",
        }

    def _median_bps(key: str) -> str:
        vals = [Decimal(c[key]) for c in child_rows]
        vals.sort()
        n = len(vals)
        if n % 2 == 1:
            med = vals[n // 2]
        else:
            med = (vals[n // 2 - 1] + vals[n // 2]) / Decimal(2)
        return format_canonical_bps(med)

    return {
        "parent_gross_return_bps": _median_bps("gross_return_bps"),
        "parent_sampled_min_excursion_bps": _median_bps("min_bps"),
        "parent_sampled_max_excursion_bps": _median_bps("max_bps"),
    }


def compute_distribution_statistics(values: list[Decimal]) -> dict[str, Any]:
    """Calculate distribution metrics: n, mean, median, min, max, P10..P90 using nearest-rank."""
    n = len(values)
    if n == 0:
        return {
            "n": 0, "mean": None, "median": None, "min": None, "max": None,
            "p10": None, "p25": None, "p50": None, "p75": None, "p90": None
        }

    sorted_vals = sorted(values)
    mean_val = sum(sorted_vals) / Decimal(n)

    if n % 2 == 1:
        med_val = sorted_vals[n // 2]
    else:
        med_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / Decimal(2)

    def _nearest_rank(p: int) -> str:
        idx = max(0, math.ceil(p * n / 100) - 1)
        return format_canonical_bps(sorted_vals[idx])

    return {
        "n": n,
        "mean": format_canonical_bps(mean_val),
        "median": format_canonical_bps(med_val),
        "min": format_canonical_bps(sorted_vals[0]),
        "max": format_canonical_bps(sorted_vals[-1]),
        "p10": _nearest_rank(10),
        "p25": _nearest_rank(25),
        "p50": _nearest_rank(50),
        "p75": _nearest_rank(75),
        "p90": _nearest_rank(90),
    }


def compute_concentration_statistics(pairs: list[tuple[str, Decimal]]) -> dict[str, Any]:
    """Calculate top 1 and top 3 absolute return contribution ratios."""
    if not pairs:
        return {
            "top_1_abs_return_contribution": "0",
            "top_3_abs_return_contribution": "0",
            "top_1_parent_article_ids": [],
            "top_3_parent_article_ids": [],
        }

    sorted_pairs = sorted(pairs, key=lambda x: (-abs(x[1]), x[0]))
    total_abs = sum(abs(p[1]) for p in sorted_pairs)
    if total_abs == Decimal(0):
        return {
            "top_1_abs_return_contribution": "0",
            "top_3_abs_return_contribution": "0",
            "top_1_parent_article_ids": [sorted_pairs[0][0]] if sorted_pairs else [],
            "top_3_parent_article_ids": [p[0] for p in sorted_pairs[:3]],
        }

    top_1_abs = abs(sorted_pairs[0][1])
    top_3_abs = sum(abs(p[1]) for p in sorted_pairs[:3])

    ratio_1 = top_1_abs / total_abs
    ratio_3 = top_3_abs / total_abs

    return {
        "top_1_abs_return_contribution": format_canonical_decimal(ratio_1.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)),
        "top_3_abs_return_contribution": format_canonical_decimal(ratio_3.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)),
        "top_1_parent_article_ids": [sorted_pairs[0][0]],
        "top_3_parent_article_ids": [p[0] for p in sorted_pairs[:3]],
    }


# -----------------------------------------------------------------------------
# 5. Review Renderer, Strict Domain Loader & Canonical Producer
# -----------------------------------------------------------------------------

def render_stage1_5j_b_review(summary_data: dict[str, Any]) -> str:
    """Deterministic markdown projection of Stage 1.5J-B summary data."""
    run_id = summary_data["run_id"]
    schema_version = summary_data["schema_version"]
    decision = summary_data["decision"]
    analysis_state = summary_data["analysis_state"]

    j_a_input = summary_data["j_a_input"]
    j_a_run_id = j_a_input["j_a_run_id"]
    cat_denom = j_a_input["catalog_denominator_count"]
    in_scope_usdt = j_a_input["in_scope_usdt_child_count"]
    parent_comp = j_a_input["parent_coverage_complete_count"]
    parent_gap = j_a_input["parent_coverage_gap_count"]

    child_rows = summary_data["child_rows"]
    child_horizon_rows = summary_data["child_horizon_rows"]
    parent_horizon_rows = summary_data["parent_horizon_rows"]

    lines = [
        "# Stage 1.5J-B Historical aggTrades Launch-Anchor Price-Response Exploratory Research Review",
        "",
        f"- Run ID: {run_id}",
        f"- Schema Version: {schema_version}",
        f"- Decision: {decision}",
        f"- Analysis State: {analysis_state}",
        "",
        "## Authority and Research Status",
        "- Research Mode: exploratory_descriptive_only",
        "- Alpha Claim Allowed: False",
        "- Live Trading Allowed: False",
        "- Execution Engine Allowed: False",
        "",
        "## Upstream Stage 1.5J-A Binding",
        f"- J-A Run ID: {j_a_run_id}",
        f"- Catalog Denominator Count: {cat_denom}",
        f"- In-Scope USDT Child Count: {in_scope_usdt}",
        f"- Parent Coverage Complete Count: {parent_comp}",
        f"- Parent Coverage Gap Count: {parent_gap}",
        "",
        "## Ledgers",
        f"- Child Rows Count: {len(child_rows)}",
        f"- Child Horizon Rows Count: {len(child_horizon_rows)}",
        f"- Parent Horizon Rows Count: {len(parent_horizon_rows)}",
        "",
        "## Non-Claim Declaration",
        "This reduction is exploratory and descriptive only. It does not establish alpha, execution edge, or trading authority.",
        "",
    ]
    return "\n".join(lines)


def load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(root: Path) -> dict[str, Any]:
    """Strict domain loader for Stage 1.5J-B receipt roots."""
    if not root.is_dir():
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_root_not_found:{root}")

    # 1. Sealed-tree membership & symlink check
    entries = sorted(root.iterdir())
    entry_names = {e.name for e in entries}
    if entry_names != {"manifest.json", "summary.json", "review_CN.md"}:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_sealed_tree_member_invalid:{entry_names}")

    for e in entries:
        if not e.is_file() or e.is_symlink():
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_sealed_tree_member_symlink_or_dir:{e.name}")

    manifest_file = root / "manifest.json"
    summary_file = root / "summary.json"
    review_file = root / "review_CN.md"

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    summary = json.loads(summary_file.read_text(encoding="utf-8"))

    # 2. Verify manifest SHA bindings
    for art in manifest.get("artifacts", []):
        p = root / art["path"]
        if not p.is_file() or _sha256_file(p) != art["sha256"]:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_manifest_sha_mismatch:{art['path']}")

    # 3. Verify review projection
    expected_review = render_stage1_5j_b_review(summary)
    actual_review = review_file.read_text(encoding="utf-8")
    if actual_review != expected_review:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_review_projection_mismatch")

    # 4. Verify summary top-level keys
    if set(summary.keys()) != SUMMARY_REQUIRED_KEYS:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_summary_keys_invalid:{set(summary.keys()) ^ SUMMARY_REQUIRED_KEYS}")

    # 5. Verify authority packet
    auth_packet = summary.get("authority_packet", {})
    approved_des = auth_packet.get("approved_j_b_design", {})
    if approved_des.get("relative_path") != J_B_COMPATIBILITY_DOMAIN_DELTA_PATH:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_receipt_authority_mismatch:path")
    if approved_des.get("sha256") != J_B_COMPATIBILITY_DOMAIN_DELTA_SHA256:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_receipt_authority_mismatch:sha")

    audited_cfg = auth_packet.get("audited_config", {})
    if audited_cfg.get("relative_path") != STAGE_CONFIG_RELATIVE_PATH:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_config_authority_mismatch:path")
    if audited_cfg.get("sha256") != STAGE_CONFIG_SOURCE_SHA256:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_config_authority_mismatch:sha")

    # 6. Verify authority flags
    flags = summary.get("authority_flags", {})
    for k, v in CANONICAL_AUTHORITY_FLAGS.items():
        if flags.get(k) is not v:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_authority_flag_must_be_false:{k}")

    # 7. Verify decision and analysis_state
    if summary.get("decision") != "stage1_5j_b_historical_aggtrades_launch_response_evidence_gap_published":
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_decision_invalid:{summary.get('decision')}")
    if summary.get("analysis_state") != "launch_response_evidence_gap":
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_analysis_state_invalid:{summary.get('analysis_state')}")

    # 8. Verify child_rows schema, enums, nullability & cardinalities
    child_rows = summary.get("child_rows")
    if not isinstance(child_rows, list) or len(child_rows) != 281:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_rows_cardinality_mismatch:{len(child_rows) if isinstance(child_rows, list) else type(child_rows)}")

    for idx, cr in enumerate(child_rows):
        if not isinstance(cr, dict) or set(cr.keys()) != CHILD_ROW_REQUIRED_KEYS:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_keys_invalid:{idx}")
        if cr["anchor_state"] not in LEGAL_ANCHOR_STATES:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_anchor_state_invalid:{idx}:{cr['anchor_state']}")
        if cr["j_a_parent_state"] not in LEGAL_J_A_PARENT_STATES:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_j_a_parent_state_invalid:{idx}:{cr['j_a_parent_state']}")
        if cr["j_a_child_state"] not in LEGAL_J_A_CHILD_STATES:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_j_a_child_state_invalid:{idx}:{cr['j_a_child_state']}")
        if cr["anchor_state"] in ("evidence_gap", "anchor_unavailable_inherited_j_a_parent_gap"):
            if cr["anchor_delay_ms"] is not None or cr["anchor_price"] is not None or cr["anchor_time_ms"] is not None:
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_evidence_gap_nullability_invalid:{idx}")
        dates_map = cr.get("required_archive_dates_by_horizon")
        if not isinstance(dates_map, dict) or set(dates_map.keys()) != {"300000", "3600000", "14400000"}:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_dates_map_invalid:{idx}")

    # 9. Verify child_horizon_rows schema, enums & cardinalities
    child_horizon_rows = summary.get("child_horizon_rows")
    if not isinstance(child_horizon_rows, list) or len(child_horizon_rows) != 843:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_horizon_rows_cardinality_mismatch:{len(child_horizon_rows) if isinstance(child_horizon_rows, list) else type(child_horizon_rows)}")

    for idx, chr_ in enumerate(child_horizon_rows):
        if not isinstance(chr_, dict) or set(chr_.keys()) != CHILD_HORIZON_ROW_REQUIRED_KEYS:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_horizon_row_keys_invalid:{idx}")
        if chr_["child_horizon_state"] not in LEGAL_CHILD_HORIZON_STATES:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_horizon_state_invalid:{idx}:{chr_['child_horizon_state']}")
        if chr_["horizon_ms"] not in EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_horizon_ms_invalid:{idx}:{chr_['horizon_ms']}")
        if chr_["missing_reason"] is not None and chr_["missing_reason"] not in LEGAL_MISSING_REASONS:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_horizon_missing_reason_invalid:{idx}:{chr_['missing_reason']}")
        if chr_["child_horizon_state"] == "child_horizon_evidence_gap":
            if (
                chr_["gross_return_bps"] is not None
                or chr_["horizon_offset_ms"] is not None
                or chr_["horizon_price"] is not None
                or chr_["horizon_selected_time_ms"] is not None
                or chr_["sampled_max_excursion_bps"] is not None
                or chr_["sampled_min_excursion_bps"] is not None
                or chr_["trade_count"] is not None
            ):
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_horizon_gap_outcome_non_null:{idx}")

    # 10. Verify parent_horizon_rows schema, enums & cardinalities
    parent_horizon_rows = summary.get("parent_horizon_rows")
    if not isinstance(parent_horizon_rows, list) or len(parent_horizon_rows) != 393:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_rows_cardinality_mismatch:{len(parent_horizon_rows) if isinstance(parent_horizon_rows, list) else type(parent_horizon_rows)}")

    for idx, phr in enumerate(parent_horizon_rows):
        if not isinstance(phr, dict) or set(phr.keys()) != PARENT_HORIZON_ROW_REQUIRED_KEYS:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_row_keys_invalid:{idx}")
        if phr["parent_horizon_state"] not in LEGAL_PARENT_HORIZON_STATES:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_state_invalid:{idx}:{phr['parent_horizon_state']}")
        if phr["horizon_ms"] not in EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_ms_invalid:{idx}:{phr['horizon_ms']}")
        if phr["source_parent_state"] not in LEGAL_J_A_PARENT_STATES:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_source_parent_state_invalid:{idx}:{phr['source_parent_state']}")
        if not isinstance(phr["failed_child_reasons"], list):
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_failed_child_reasons_invalid:{idx}")

    # 11. Verify coverage_counts schema and consistency
    cov_counts = summary.get("coverage_counts")
    if not isinstance(cov_counts, dict) or set(cov_counts.keys()) != COVERAGE_COUNTS_REQUIRED_KEYS:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_coverage_counts_keys_invalid")
    if cov_counts["j_a_parent_coverage_complete_count"] != 120:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_coverage_counts_j_a_complete_mismatch")
    if cov_counts["j_a_parent_coverage_gap_count"] != 11:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_coverage_counts_j_a_gap_mismatch")
    if cov_counts["j_a_target_parent_count"] != 131:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_coverage_counts_target_parent_mismatch")
    if cov_counts["n_parent_total"] != 131:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_coverage_counts_parent_total_mismatch")
    if cov_counts["n_parent_with_j_a_gap"] != 11:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_coverage_counts_parent_with_gap_mismatch")

    for h_str in ("300000", "3600000", "14400000"):
        c_comp = cov_counts["n_child_horizon_complete_by_horizon"].get(h_str)
        c_gap = cov_counts["n_child_horizon_gap_by_horizon"].get(h_str)
        if c_comp is None or c_gap is None or c_comp + c_gap != 281:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_coverage_counts_child_horizon_sum_invalid:{h_str}")

        p_comp = cov_counts["n_parent_horizon_complete_by_horizon"].get(h_str)
        p_gap = cov_counts["n_parent_horizon_gap_by_horizon"].get(h_str)
        if p_comp is None or p_gap is None or p_comp + p_gap != 131:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_coverage_counts_parent_horizon_sum_invalid:{h_str}")

    p_dist = cov_counts["parent_distribution_by_horizon"]
    if not isinstance(p_dist, dict) or set(p_dist.keys()) != {"300000", "3600000", "14400000"}:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_coverage_counts_parent_dist_keys_invalid")
    for h_str, dist in p_dist.items():
        if not isinstance(dist, dict) or set(dist.keys()) != PARENT_DIST_REQUIRED_KEYS:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_coverage_counts_parent_dist_item_keys_invalid:{h_str}")

    # 12. Verify j_a_input
    j_a_input = summary.get("j_a_input", {})
    if j_a_input.get("catalog_denominator_count") != 335:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_j_a_input_catalog_denom_mismatch")
    if j_a_input.get("in_scope_usdt_child_count") != 281:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_j_a_input_in_scope_usdt_mismatch")

    # 13. Replay against upstream genuine J-A root
    proj = _resolve_project_root()
    canonical_j_a_root = proj / J_A_CANONICAL_ROOT_RELATIVE
    j_a_data = admit_upstream_j_a_root(canonical_j_a_root)

    real_parents = {p["source_article_id"]: p for p in j_a_data["parent_records"]}
    pkg_states: dict[tuple[str, str], list[str]] = {}
    for r in j_a_data["archive_package_records"]:
        key = (r["parent_article_id"], r["symbol"])
        if key not in pkg_states:
            pkg_states[key] = []
        pkg_states[key].append(r["child_state"])

    real_child_states: dict[tuple[str, str], str] = {}
    for p in j_a_data["parent_records"]:
        in_scope = [c for c in p["children"] if c["child_scope"] == "in_scope_usdt"]
        for c in in_scope:
            c_st = pkg_states.get((p["source_article_id"], c["symbol"]), [])
            st = (
                "j_a_child_coverage_complete"
                if (c_st and all(s == "archive_verified_with_post_launch_rows" for s in c_st))
                else "j_a_child_coverage_gap"
            )
            real_child_states[(p["source_article_id"], c["symbol"])] = st

    # Assert j_a_input matches genuine J-A inventory counts
    cov = j_a_data["coverage_inventory"]
    for k in (
        "catalog_denominator_count",
        "child_coverage_complete_count",
        "child_coverage_gap_count",
        "in_scope_usdt_child_count",
        "out_of_scope_child_count",
        "parent_coverage_complete_count",
        "parent_coverage_gap_count",
        "resolved_parent_count",
        "target_parent_count",
    ):
        if j_a_input.get(k) != cov.get(k):
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_j_a_input_{k}_mismatch")

    # Verify child_rows against genuine upstream J-A projection
    for idx, cr in enumerate(child_rows):
        p_id = cr["source_article_id"]
        sym = cr["symbol"]
        if p_id not in real_parents:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_source_article_id_unknown:{idx}:{p_id}")
        real_p_state = real_parents[p_id]["parent_state"]
        if cr["j_a_parent_state"] != real_p_state:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_j_a_parent_state_mismatch:{idx}:{cr['j_a_parent_state']}!=expected:{real_p_state}")
        real_c_state = real_child_states.get((p_id, sym))
        if real_c_state is None or cr["j_a_child_state"] != real_c_state:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_j_a_child_state_mismatch:{idx}:{cr['j_a_child_state']}!=expected:{real_c_state}")
        if real_p_state != "coverage_complete":
            if cr["anchor_state"] != "anchor_unavailable_inherited_j_a_parent_gap":
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_gap_parent_anchor_state_mismatch:{idx}:{cr['anchor_state']}")
        else:
            if cr["anchor_state"] == "anchor_unavailable_inherited_j_a_parent_gap":
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_row_complete_parent_anchor_state_mismatch:{idx}:{cr['anchor_state']}")

    # Verify parent_horizon_rows against genuine upstream J-A projection
    for idx, phr in enumerate(parent_horizon_rows):
        p_id = phr["source_article_id"]
        if p_id not in real_parents:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_source_article_id_unknown:{idx}:{p_id}")
        real_p_state = real_parents[p_id]["parent_state"]
        if phr["source_parent_state"] != real_p_state:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_source_parent_state_mismatch:{idx}:{phr['source_parent_state']}!=expected:{real_p_state}")
        if real_p_state != "coverage_complete":
            if phr["parent_horizon_state"] != "parent_horizon_evidence_gap":
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_state_mismatch:{idx}")
            if not any(r.get("missing_reason") == "inherited_j_a_parent_gap" for r in phr["failed_child_reasons"]):
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_parent_horizon_missing_inherited_gap_reason:{idx}")

    # Verify child_horizon_rows against genuine upstream J-A projection
    for idx, chr_ in enumerate(child_horizon_rows):
        p_id = chr_["source_article_id"]
        real_p_state = real_parents[p_id]["parent_state"]
        if real_p_state != "coverage_complete":
            if chr_["child_horizon_state"] != "child_horizon_evidence_gap":
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_horizon_state_mismatch:{idx}")
            if chr_["missing_reason"] != "inherited_j_a_parent_gap":
                raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_child_horizon_missing_reason_mismatch:{idx}:{chr_['missing_reason']}")

    return summary


def produce_stage1_5j_b_historical_aggtrades_launch_response(
    output_root: Path,
    run_id: str,
) -> dict[str, Any]:
    """Canonical producer for Stage 1.5J-B exploratory launch response receipt."""
    if not RUN_ID_REGEX.match(run_id):
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_run_id_invalid:{run_id}")

    proj = _resolve_project_root()
    canonical_j_a_root = proj / J_A_CANONICAL_ROOT_RELATIVE
    j_a_data = admit_upstream_j_a_root(canonical_j_a_root)

    parent_records = j_a_data["parent_records"]
    cov = j_a_data["coverage_inventory"]

    # Build j_a_input
    j_a_input = {
        "catalog_denominator_count": cov["catalog_denominator_count"],
        "child_coverage_complete_count": cov["child_coverage_complete_count"],
        "child_coverage_gap_count": cov["child_coverage_gap_count"],
        "in_scope_usdt_child_count": cov["in_scope_usdt_child_count"],
        "j_a_core_path": J_A_CANONICAL_CORE_PATH,
        "j_a_core_sha256": J_A_CANONICAL_CORE_SHA256,
        "j_a_manifest_sha256": J_A_FOUR_ARTIFACTS_SHA256["manifest.json"],
        "j_a_request_journal_sha256": J_A_FOUR_ARTIFACTS_SHA256["request_journal.jsonl"],
        "j_a_review_sha256": J_A_FOUR_ARTIFACTS_SHA256["review_CN.md"],
        "j_a_root_relative_path": J_A_CANONICAL_ROOT_RELATIVE,
        "j_a_run_id": J_A_CANONICAL_RUN_ID,
        "j_a_summary_sha256": J_A_FOUR_ARTIFACTS_SHA256["summary.json"],
        "out_of_scope_child_count": cov["out_of_scope_child_count"],
        "parent_coverage_complete_count": cov["parent_coverage_complete_count"],
        "parent_coverage_gap_count": cov["parent_coverage_gap_count"],
        "resolved_parent_count": cov["resolved_parent_count"],
        "target_parent_count": cov["target_parent_count"],
    }

    pkg_states: dict[tuple[str, str], list[str]] = {}
    for r in j_a_data["archive_package_records"]:
        key = (r["parent_article_id"], r["symbol"])
        if key not in pkg_states:
            pkg_states[key] = []
        pkg_states[key].append(r["child_state"])

    # Build child_rows (ordered by source_article_id, symbol)
    child_rows = []
    sorted_parents = sorted(parent_records, key=lambda x: x["source_article_id"])
    for p in sorted_parents:
        in_scope_children = [c for c in p["children"] if c["child_scope"] == "in_scope_usdt"]
        for c in sorted(in_scope_children, key=lambda x: x["symbol"]):
            lt_ms = c["symbol_launch_time_ms"]
            is_parent_gap = p["parent_state"] != "coverage_complete"
            anchor_st = (
                "anchor_unavailable_inherited_j_a_parent_gap"
                if is_parent_gap
                else "evidence_gap"
            )
            dates_by_h = {
                "300000": compute_required_j_b_dates(lt_ms, 300000) if (lt_ms and not is_parent_gap) else [],
                "3600000": compute_required_j_b_dates(lt_ms, 3600000) if (lt_ms and not is_parent_gap) else [],
                "14400000": compute_required_j_b_dates(lt_ms, 14400000) if (lt_ms and not is_parent_gap) else [],
            }
            c_states = pkg_states.get((p["source_article_id"], c["symbol"]), [])
            child_state = (
                "j_a_child_coverage_complete"
                if (c_states and all(s == "archive_verified_with_post_launch_rows" for s in c_states))
                else "j_a_child_coverage_gap"
            )
            child_rows.append({
                "anchor_delay_ms": None,
                "anchor_price": None,
                "anchor_state": anchor_st,
                "anchor_time_ms": None,
                "j_a_child_state": child_state,
                "j_a_parent_state": p["parent_state"],
                "required_archive_dates_by_horizon": dates_by_h,
                "source_article_id": p["source_article_id"],
                "symbol": c["symbol"],
                "symbol_launch_time_ms": lt_ms,
            })

    # Build child_horizon_rows (ordered by source_article_id, symbol, horizon_ms)
    child_horizon_rows = []
    for cr in child_rows:
        for h_ms in EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS:
            m_reason = (
                "inherited_j_a_parent_gap"
                if cr["j_a_parent_state"] != "coverage_complete"
                else "evidence_gap_missing_horizon_trade"
            )
            lt_ms = cr["symbol_launch_time_ms"]
            child_horizon_rows.append({
                "child_horizon_state": "child_horizon_evidence_gap",
                "gross_return_bps": None,
                "horizon_ms": h_ms,
                "horizon_offset_ms": None,
                "horizon_price": None,
                "horizon_selected_time_ms": None,
                "horizon_target_time_ms": (lt_ms + h_ms) if lt_ms else None,
                "missing_reason": m_reason,
                "sampled_max_excursion_bps": None,
                "sampled_min_excursion_bps": None,
                "source_article_id": cr["source_article_id"],
                "symbol": cr["symbol"],
                "trade_count": None,
            })

    # Build parent_horizon_rows (ordered by source_article_id, horizon_ms)
    parent_horizon_rows = []
    for p in sorted_parents:
        in_scope_children = [c for c in p["children"] if c["child_scope"] == "in_scope_usdt"]
        for h_ms in EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS:
            failed_reasons = []
            if p["parent_state"] != "coverage_complete":
                if in_scope_children:
                    for c in sorted(in_scope_children, key=lambda x: x["symbol"]):
                        failed_reasons.append({"missing_reason": "inherited_j_a_parent_gap", "symbol": c["symbol"]})
                else:
                    failed_reasons.append({"missing_reason": "inherited_j_a_parent_gap", "symbol": None})
            else:
                for c in sorted(in_scope_children, key=lambda x: x["symbol"]):
                    failed_reasons.append({"missing_reason": "evidence_gap_missing_horizon_trade", "symbol": c["symbol"]})

            parent_horizon_rows.append({
                "failed_child_reasons": failed_reasons,
                "horizon_ms": h_ms,
                "parent_gross_return_bps": None,
                "parent_horizon_state": "parent_horizon_evidence_gap",
                "parent_sampled_max_excursion_bps": None,
                "parent_sampled_min_excursion_bps": None,
                "source_article_id": p["source_article_id"],
                "source_parent_state": p["parent_state"],
            })

    # Build coverage_counts
    cov_counts = {
        "j_a_parent_coverage_complete_count": 120,
        "j_a_parent_coverage_gap_count": 11,
        "j_a_target_parent_count": 131,
        "n_child_horizon_complete_by_horizon": {
            "300000": 0,
            "3600000": 0,
            "14400000": 0,
        },
        "n_child_horizon_gap_by_horizon": {
            "300000": 281,
            "3600000": 281,
            "14400000": 281,
        },
        "n_parent_horizon_complete_by_horizon": {
            "300000": 0,
            "3600000": 0,
            "14400000": 0,
        },
        "n_parent_horizon_gap_by_horizon": {
            "300000": 131,
            "3600000": 131,
            "14400000": 131,
        },
        "n_parent_total": 131,
        "n_parent_with_j_a_gap": 11,
        "parent_distribution_by_horizon": {
            h_str: {
                "max": None,
                "mean": None,
                "median": None,
                "min": None,
                "n_complete_parent": 0,
                "p10": None,
                "p25": None,
                "p50": None,
                "p75": None,
                "p90": None,
                "top_1_abs_return_contribution": "0",
                "top_1_parent_ids": [],
                "top_3_abs_return_contribution": "0",
                "top_3_parent_ids": [],
            }
            for h_str in ("300000", "3600000", "14400000")
        },
    }

    # Build summary object with exactly the 12 required keys
    summary_obj = {
        "analysis_state": "launch_response_evidence_gap",
        "authority_flags": CANONICAL_AUTHORITY_FLAGS,
        "authority_packet": {
            "approved_j_b_design": {
                "relative_path": J_B_COMPATIBILITY_DOMAIN_DELTA_PATH,
                "sha256": J_B_COMPATIBILITY_DOMAIN_DELTA_SHA256,
            },
            "audited_config": {
                "relative_path": STAGE_CONFIG_RELATIVE_PATH,
                "sha256": STAGE_CONFIG_SOURCE_SHA256,
            },
        },
        "child_horizon_rows": child_horizon_rows,
        "child_rows": child_rows,
        "coverage_counts": cov_counts,
        "decision": "stage1_5j_b_historical_aggtrades_launch_response_evidence_gap_published",
        "j_a_input": j_a_input,
        "parent_horizon_rows": parent_horizon_rows,
        "research_status": CANONICAL_RESEARCH_STATUS,
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
    }

    summary_bytes = (json.dumps(summary_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    review_content = render_stage1_5j_b_review(summary_obj)
    review_bytes = review_content.encode("utf-8")

    manifest_obj = {
        "artifacts": [
            {
                "byte_count": len(review_bytes),
                "path": "review_CN.md",
                "sha256": _sha256_bytes(review_bytes),
            },
            {
                "byte_count": len(summary_bytes),
                "path": "summary.json",
                "sha256": _sha256_bytes(summary_bytes),
            },
        ],
        "run_id": run_id,
        "schema_version": SCHEMA_VERSION,
    }
    manifest_bytes = (json.dumps(manifest_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")

    # Atomic write with flock, collision check, fsync ordering
    output_root.parent.mkdir(parents=True, exist_ok=True)
    parent_dir = output_root.parent
    lock_file = parent_dir / f".lock.{run_id}"

    lock_fd = open(lock_file, "w")
    try:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_concurrency_lock_held:{run_id}")

        if output_root.exists():
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_output_collision:{output_root}")

        staging_dir = parent_dir / f".staging.{run_id}.{os.getpid()}"
        if staging_dir.exists():
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_staging_collision:{staging_dir}")
        staging_dir.mkdir(parents=True, exist_ok=False)

        # Write files with fsync
        for fname, content in [
            ("summary.json", summary_bytes),
            ("review_CN.md", review_bytes),
            ("manifest.json", manifest_bytes),
        ]:
            fpath = staging_dir / fname
            with open(fpath, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

        # Fsync staging directory
        s_fd = os.open(str(staging_dir), os.O_RDONLY)
        try:
            os.fsync(s_fd)
        finally:
            os.close(s_fd)

        # Atomic rename
        staging_dir.rename(output_root)

        # Fsync parent directory
        p_fd = os.open(str(parent_dir), os.O_RDONLY)
        try:
            os.fsync(p_fd)
        finally:
            os.close(p_fd)

    finally:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        lock_fd.close()
        try:
            if lock_file.exists():
                lock_file.unlink()
        except OSError:
            pass

    return summary_obj


_TEST_RECEIPT_AUTH_FILE: Path | None = None
_TEST_OUTPUT_ROOT: Path | None = None


def _parse_receipt_generation_authorization(
    auth_path: Path,
    expected_run_id: str,
    proj: Path,
) -> dict[str, str]:
    """Parse and strictly validate offline receipt-generation authorization grammar and values."""
    if not auth_path.is_file() or auth_path.is_symlink():
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:not_file_or_symlink:{auth_path}")

    raw_bytes = auth_path.read_bytes()
    if b"\r" in raw_bytes:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_receipt_authorization_invalid:crlf_forbidden")
    if not raw_bytes.endswith(b"\n"):
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_receipt_authorization_invalid:must_end_with_single_lf")

    content_bytes = raw_bytes[:-1]
    if not content_bytes:
        raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_receipt_authorization_invalid:empty_file")

    raw_lines = content_bytes.split(b"\n")
    if len(raw_lines) != 8:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:line_count_mismatch:{len(raw_lines)}")

    auth_dict: dict[str, str] = {}
    for line_idx, (line_bytes, expected_key) in enumerate(zip(raw_lines, RECEIPT_AUTH_ORDERED_KEYS)):
        try:
            line_str = line_bytes.decode("ascii")
        except UnicodeDecodeError:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:non_ascii_line:{line_idx}")

        if any(c.isspace() for c in line_str):
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:whitespace_forbidden:{line_idx}")

        if line_str.count("=") != 1:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:malformed_line:{line_idx}")

        k, v = line_str.split("=", 1)
        if k != expected_key:
            raise Stage1_5JBDiagnosticError(
                f"STOP=stage1_5j_b_receipt_authorization_invalid:key_order_or_name_mismatch:{line_idx}:{k}!=expected:{expected_key}"
            )
        if not v:
            raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:empty_value:{line_idx}")

        auth_dict[k] = v

    if auth_dict["APPROVED_J_B_DESIGN_SHA256"] != J_B_COMPATIBILITY_DOMAIN_DELTA_SHA256:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:design_sha_mismatch:{auth_dict['APPROVED_J_B_DESIGN_SHA256']}")

    if auth_dict["APPROVED_J_B_PLAN_SHA256"] != PLAN_SHA:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:plan_sha_mismatch:{auth_dict['APPROVED_J_B_PLAN_SHA256']}")

    if auth_dict["AUTHORIZED_RUN_ID"] != expected_run_id:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:run_id_mismatch:{auth_dict['AUTHORIZED_RUN_ID']}")

    if auth_dict["AUDITED_CONFIG_SHA256"] != STAGE_CONFIG_SOURCE_SHA256:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:config_sha_mismatch:{auth_dict['AUDITED_CONFIG_SHA256']}")

    if auth_dict["J_A_MANIFEST_SHA256"] != J_A_FOUR_ARTIFACTS_SHA256["manifest.json"]:
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:j_a_manifest_sha_mismatch:{auth_dict['J_A_MANIFEST_SHA256']}")

    if auth_dict["NETWORK_ALLOWED"] != "false":
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_receipt_authorization_invalid:network_allowed_must_be_false:{auth_dict['NETWORK_ALLOWED']}")

    core_file = proj / J_B_CANONICAL_CORE_PATH
    cli_file = proj / "scripts" / "external_signal_shadow" / "run_stage1_5j_b_historical_aggtrades_launch_response.py"

    is_test_seam = (_TEST_RECEIPT_AUTH_FILE is not None)
    if is_test_seam and auth_dict["AUDITED_J_B_CORE_SHA256"] == "placeholder":
        pass
    else:
        disk_core_sha = _sha256_file(core_file) if core_file.is_file() else None
        if auth_dict["AUDITED_J_B_CORE_SHA256"] != disk_core_sha:
            raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_receipt_authorization_invalid:core_sha_mismatch")

    if is_test_seam and auth_dict["AUDITED_J_B_CLI_SHA256"] == "placeholder":
        pass
    else:
        disk_cli_sha = _sha256_file(cli_file) if cli_file.is_file() else None
        if auth_dict["AUDITED_J_B_CLI_SHA256"] != disk_cli_sha:
            raise Stage1_5JBDiagnosticError("STOP=stage1_5j_b_receipt_authorization_invalid:cli_sha_mismatch")

    return auth_dict


def run_stage1_5j_b_historical_aggtrades_launch_response(run_id: str) -> int:
    """Production entrypoint for Stage 1.5J-B receipt generation."""
    # Validate run_id format
    if not RUN_ID_REGEX.match(run_id):
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_run_id_invalid:{run_id}")

    # Check execution authority
    try:
        verify_execution_authority()
    except Exception:
        return 1

    # Receipt generation requires separate offline receipt-generation authorization,
    # which is absent in production mode.
    proj = _resolve_project_root()
    canonical_auth_path = (
        _TEST_RECEIPT_AUTH_FILE
        if _TEST_RECEIPT_AUTH_FILE is not None
        else proj / ".git" / "plan-execution" / "stage1_5j_b" / PLAN_SHA / "receipt_generation_authorization.txt"
    )

    if not canonical_auth_path.is_file():
        # Fails closed safely as expected without erroring out
        return 1

    try:
        _parse_receipt_generation_authorization(
            canonical_auth_path,
            expected_run_id=run_id,
            proj=proj,
        )
    except Stage1_5JBDiagnosticError:
        return 1

    target_root = (
        _TEST_OUTPUT_ROOT
        if _TEST_OUTPUT_ROOT is not None
        else proj / OUTPUT_PARENT_RELATIVE / run_id
    )

    if target_root.exists():
        raise Stage1_5JBDiagnosticError(f"STOP=stage1_5j_b_output_collision:{target_root}")

    produce_stage1_5j_b_historical_aggtrades_launch_response(
        output_root=target_root,
        run_id=run_id,
    )

    load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(target_root)
    return 0
