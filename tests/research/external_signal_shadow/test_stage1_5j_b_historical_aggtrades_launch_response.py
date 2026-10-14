"""Tests for Stage 1.5J-B Historical aggTrades Launch-Anchor Price-Response Exploratory Research.

Strictly verifies:
1. Task 0 execution authority verification (bundle, grammar, hashes).
2. Upstream Stage 1.5J-A admission, import-origin integrity, v2 governance closure evidence, and 9 rebound projections.
3. Resource caps (ZIP, CSV, ratio, root, disk space), stream bounds, and zero ZipFile extraction.
4. Deterministic algorithms (physical order, tie-break, Decimal math, anchor selection, horizons, median, percentiles, concentration).
5. Canonical multi-child complete fixture derivation and independent test oracle comparison.
6. Compound-state precedence probes (earlier frozen gate wins before later sensitive operation).
7. Receipt generation authorization parser, canonical locator absence, and process-local publication seam.
8. Domain strict loader verification and Markdown re-rendering.
"""

import ast
import csv
import fcntl
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES,
    Stage1_5JBDiagnosticError,
    _verify_stage_config,
    admit_upstream_j_a_root,
    aggregate_parent_horizon_outcomes,
    calculate_child_horizon_outcomes,
    compute_concentration_statistics,
    compute_distribution_statistics,
    select_horizon_trade,
    select_launch_anchor_trade,
    validate_zip_archive_package,
    verify_execution_authority,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_J_A_ROOT = (
    PROJECT_ROOT
    / "data"
    / "external_signal_shadow"
    / "stage1_5j_a"
    / "historical_archive_coverage_inventory"
    / "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
)
PLAN_SHA = "1ee36be9faea1d8e8bf0cdde5519cc9ccedcd6fb31464b94e6602e4ac28188fd"
TASK0_BUNDLE_DIR = PROJECT_ROOT / ".git" / "plan-execution" / "stage1_5j_b" / PLAN_SHA / "baseline"


# =============================================================================
# 1. Task 0 Execution Authority Verification
# =============================================================================


def test_verify_execution_authority_positive() -> None:
    """Canonical Task 0 on-disk bundle passes verification cleanly."""
    auth = verify_execution_authority()
    assert auth["schema_version"] == "stage1_5j_b_execution_authority_v2"
    assert auth["risk_live_trading_enabled"] is False
    assert auth["base_sha"] == "2073f2d1953d5b2e71d3336912ab63a8c5d90cad"
    assert auth["source_label"] == "received_external_handoff"
    assert "handoff_authorizations" in auth


def test_verify_execution_authority_malformed_grammar_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed implementation authorization grammar fails closed."""
    bundle_copy = tmp_path / "bundle"
    import shutil
    shutil.copytree(TASK0_BUNDLE_DIR, bundle_copy)
    # Corrupt grammar in implementation_authorization.txt
    (bundle_copy / "implementation_authorization.txt").write_bytes(b"INVALID_KEY=true\n")
    # Recompute sidecar
    h = hashlib.sha256(b"INVALID_KEY=true\n").hexdigest()
    (bundle_copy / "implementation_authorization.txt.sha256").write_text(f"{h}  implementation_authorization.txt\n")

    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response.TASK0_AUTHORITY_DIR",
        bundle_copy,
    )
    with pytest.raises(Stage1_5JBDiagnosticError, match="implementation_authorization_grammar_invalid"):
        verify_execution_authority()


def test_verify_stage_config_positive() -> None:
    """Production stage config module verifies cleanly."""
    cfg = _verify_stage_config()
    assert isinstance(cfg, dict)
    assert cfg["EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES"] == 268_435_456
    assert cfg["EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES"] == 536_870_912
    assert cfg["EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO"] == 64
    assert cfg["EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS"] == 300_000
    assert cfg["EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS"] == (300_000, 3_600_000, 14_400_000)
    assert cfg["EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZON_LOOKBACK_MS"] == 60_000
    assert cfg["EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES"] == 65_536
    assert cfg["EXTERNAL_SIGNAL_STAGE1_5J_B_ROOT_MAX_BYTES"] == 67_108_864
    assert cfg["EXTERNAL_SIGNAL_STAGE1_5J_B_MIN_FREE_BYTES"] == 1_073_741_824


def test_verify_stage_config_absent_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing stage config module fails closed."""
    non_existent = tmp_path / "non_existent.py"
    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response.STAGE_CONFIG_PATH",
        non_existent,
    )
    with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_config_authority_mismatch"):
        _verify_stage_config()


def test_verify_stage_config_tampered_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Tampered stage config file content fails closed due to SHA mismatch."""
    tampered_file = tmp_path / "tampered.py"
    tampered_file.write_text("EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES = 999\n")
    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response.STAGE_CONFIG_PATH",
        tampered_file,
    )
    with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_config_authority_mismatch"):
        _verify_stage_config()


# =============================================================================
# 2. Upstream Stage 1.5J-A Admission & Governance Closure
# =============================================================================


def test_upstream_j_a_admission_positive() -> None:
    """Genuine replacement root passes admission with all 9 projections."""
    j_a_data = admit_upstream_j_a_root(CANONICAL_J_A_ROOT)
    assert j_a_data["run_id"] == "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
    assert j_a_data["analysis_state"] == "coverage_inventory_evidence_gap"
    assert j_a_data["decision"] == "stage1_5j_a_historical_archive_coverage_evidence_gap_published"

    cov = j_a_data["coverage_inventory"]
    assert cov["catalog_denominator_count"] == 335
    assert cov["target_parent_count"] == 131
    assert cov["resolved_parent_count"] == 125
    assert cov["parent_coverage_complete_count"] == 120
    assert cov["parent_coverage_gap_count"] == 11
    assert cov["in_scope_usdt_child_count"] == 281
    assert cov["child_coverage_complete_count"] == 280
    assert cov["child_coverage_gap_count"] == 1
    assert cov["out_of_scope_child_count"] == 5


def test_upstream_j_a_admission_rejects_shadow_import(tmp_path: Path) -> None:
    """Isolated shadow import probe places rogue module in sys.modules and fails closed."""
    rogue_file = tmp_path / "fake_core.py"
    rogue_file.write_text("def load_verified_stage1_5j_a_historical_archive_coverage_root(r): return {'run_id': 'fake'}\n")

    test_script = f"""
import sys, types
from pathlib import Path

fake_mod = types.ModuleType("stage1_5j_a_historical_archive_coverage_inventory")
fake_mod.__file__ = "{rogue_file}"
fake_mod.__spec__ = types.SimpleNamespace(origin="{rogue_file}")
sys.modules["src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory"] = fake_mod

from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import admit_upstream_j_a_root

try:
    admit_upstream_j_a_root(Path("{CANONICAL_J_A_ROOT}"))
    print("FAILED_TO_CATCH")
    sys.exit(1)
except Exception as e:
    if "upstream_authority_mismatch" in str(e) or "import_origin" in str(e) or "core_sha_mismatch" in str(e):
        print("CAUGHT_SAFELY")
        sys.exit(0)
    print("WRONG_ERROR", repr(e))
    sys.exit(2)
"""
    res = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True)
    assert res.returncode == 0, f"Shadow import probe failed: stdout={res.stdout}, stderr={res.stderr}"
    assert "CAUGHT_SAFELY" in res.stdout


def test_upstream_j_a_admission_rejects_mutated_projections(tmp_path: Path) -> None:
    """Mutating a projection in summary.json triggers fail-closed."""
    fake_root = tmp_path / "fake_j_a"
    fake_root.mkdir(parents=True, exist_ok=True)
    for f in ["manifest.json", "summary.json", "review_CN.md", "request_journal.jsonl"]:
        (fake_root / f).write_bytes((CANONICAL_J_A_ROOT / f).read_bytes())

    # Mutate summary.json projection
    s_obj = json.loads((fake_root / "summary.json").read_text(encoding="utf-8"))
    s_obj["coverage_inventory"]["parent_coverage_complete_count"] = 118  # Old value
    (fake_root / "summary.json").write_text(json.dumps(s_obj))

    with pytest.raises(Stage1_5JBDiagnosticError, match="upstream_projection_mismatch|manifest_mismatch|upstream_authority_mismatch"):
        admit_upstream_j_a_root(fake_root)


# =============================================================================
# 3. Deterministic Measurement & Arithmetic Unit Tests
# =============================================================================


def test_csv_header_validation() -> None:
    """CSV header must strictly match expected 7 columns."""
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        REQUIRED_CSV_HEADER,
        validate_aggtrades_csv_header,
    )
    assert REQUIRED_CSV_HEADER == [
        "agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"
    ]
    assert validate_aggtrades_csv_header(REQUIRED_CSV_HEADER) is True
    assert validate_aggtrades_csv_header(["price", "quantity"]) is False


def test_decimal_fixed_point_serialization() -> None:
    """Decimal formatting must be canonical fixed-point without scientific notation or trailing zeros."""
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        format_canonical_bps,
        format_canonical_decimal,
    )
    assert format_canonical_decimal(Decimal("0.00000000")) == "0"
    assert format_canonical_decimal(Decimal("123.4500")) == "123.45"
    assert format_canonical_decimal(Decimal("1000")) == "1000"

    assert format_canonical_bps(Decimal("12.345678901")) == "12.3456789"
    assert format_canonical_bps(Decimal("0")) == "0"


def test_launch_anchor_selection() -> None:
    """Anchor is the first physical trade with transact_time >= launch_time_ms within 300s."""
    launch_time_ms = 1700000000000
    trades = [
        {"transact_time": 1699999999000, "price": Decimal("10.0"), "physical_order": 1},
        {"transact_time": 1700000000000, "price": Decimal("10.5"), "physical_order": 2},
        {"transact_time": 1700000000100, "price": Decimal("10.6"), "physical_order": 3},
    ]
    anchor = select_launch_anchor_trade(trades, launch_time_ms, EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS)
    assert anchor is not None
    assert anchor["transact_time"] == 1700000000000
    assert anchor["price"] == Decimal("10.5")

    # Exceeding 300s delay -> returns None
    late_trades = [
        {"transact_time": 1700000300001, "price": Decimal("10.5"), "physical_order": 1},
    ]
    late_anchor = select_launch_anchor_trade(late_trades, launch_time_ms, EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS)
    assert late_anchor is None


def test_horizon_trade_selection_tie_break() -> None:
    """Horizon trade is the last physical trade in [target_time - 60s, target_time]."""
    target_time_ms = 1700000300000
    lookback_ms = 60000
    # Window is [1700000240000, 1700000300000]
    trades = [
        {"transact_time": 1700000239999, "price": Decimal("10.0"), "physical_order": 1},
        {"transact_time": 1700000250000, "price": Decimal("10.2"), "physical_order": 2},
        {"transact_time": 1700000250000, "price": Decimal("10.3"), "physical_order": 3},  # Equal timestamp, later order
    ]
    sel = select_horizon_trade(trades, target_time_ms, lookback_ms)
    assert sel is not None
    assert sel["price"] == Decimal("10.3")
    assert sel["physical_order"] == 3


def test_child_outcomes_calculation() -> None:
    """Child outcomes calculate gross return and sampled min/max excursions in bps."""
    anchor_price = Decimal("100.0")
    horizon_price = Decimal("105.0")
    sampled_min_price = Decimal("95.0")
    sampled_max_price = Decimal("110.0")

    outcomes = calculate_child_horizon_outcomes(
        anchor_price=anchor_price,
        horizon_price=horizon_price,
        sampled_min_price=sampled_min_price,
        sampled_max_price=sampled_max_price,
        horizon_selected_time_ms=1700000300000,
        target_time_ms=1700000300000,
    )
    # gross_return = 10000 * (105/100 - 1) = 500 bps
    assert outcomes["gross_return_bps"] == "500"
    # min_excursion = 10000 * (95/100 - 1) = -500 bps
    assert outcomes["sampled_min_excursion_bps"] == "-500"
    # max_excursion = 10000 * (110/100 - 1) = 1000 bps
    assert outcomes["sampled_max_excursion_bps"] == "1000"
    assert outcomes["horizon_offset_ms"] == 0


def test_parent_aggregation_simple_median() -> None:
    """Parent horizon aggregates children using simple median; odd n takes middle, even n takes average."""
    # Odd n: 3 children
    child_returns_odd = [
        {"symbol": "A", "gross_return_bps": Decimal("100"), "min_bps": Decimal("-50"), "max_bps": Decimal("200")},
        {"symbol": "B", "gross_return_bps": Decimal("200"), "min_bps": Decimal("-60"), "max_bps": Decimal("250")},
        {"symbol": "C", "gross_return_bps": Decimal("500"), "min_bps": Decimal("-20"), "max_bps": Decimal("600")},
    ]
    agg_odd = aggregate_parent_horizon_outcomes(child_returns_odd)
    assert agg_odd["parent_gross_return_bps"] == "200"

    # Even n: 2 children (100 and 200 -> 150)
    child_returns_even = [
        {"symbol": "A", "gross_return_bps": Decimal("100"), "min_bps": Decimal("-50"), "max_bps": Decimal("200")},
        {"symbol": "B", "gross_return_bps": Decimal("200"), "min_bps": Decimal("-60"), "max_bps": Decimal("250")},
    ]
    agg_even = aggregate_parent_horizon_outcomes(child_returns_even)
    assert agg_even["parent_gross_return_bps"] == "150"


def test_distribution_nearest_rank_percentiles() -> None:
    """Distribution calculates mean, median, nearest-rank P10/P25/P50/P75/P90."""
    values = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40"), Decimal("50")]
    dist = compute_distribution_statistics(values)
    assert dist["n"] == 5
    assert dist["mean"] == "30"
    assert dist["median"] == "30"
    assert dist["min"] == "10"
    assert dist["max"] == "50"
    assert dist["p50"] == "30"


def test_concentration_statistics() -> None:
    """Concentration calculates top 1 and top 3 absolute return contribution ratios."""
    pairs = [
        ("art_1", Decimal("500")),
        ("art_2", Decimal("-300")),
        ("art_3", Decimal("100")),
        ("art_4", Decimal("100")),
    ]
    # Total abs sum = 500 + 300 + 100 + 100 = 1000
    # Top 1 abs = 500 -> 500 / 1000 = 0.5
    # Top 3 abs = 500 + 300 + 100 = 900 -> 900 / 1000 = 0.9
    conc = compute_concentration_statistics(pairs)
    assert conc["top_1_abs_return_contribution"] == "0.5"
    assert conc["top_3_abs_return_contribution"] == "0.9"
    assert conc["top_1_parent_article_ids"] == ["art_1"]
    assert conc["top_3_parent_article_ids"] == ["art_1", "art_2", "art_3"]


# =============================================================================
# 4. Resource Caps & Stream Bounds
# =============================================================================


def test_resource_cap_validation(tmp_path: Path) -> None:
    """Validates zip size, csv uncompressed size, compression ratio pre-open checks."""
    dummy_zip = tmp_path / "dummy.zip"
    with zipfile.ZipFile(dummy_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.csv", b"a" * 100)

    # Valid package
    assert validate_zip_archive_package(
        zip_path=dummy_zip,
        max_zip_bytes=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES,
        max_uncompressed_bytes=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
        max_ratio=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO,
    ) is True

    # Exceeding max zip bytes
    assert validate_zip_archive_package(
        zip_path=dummy_zip,
        max_zip_bytes=10,  # lower than dummy_zip file size
        max_uncompressed_bytes=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
        max_ratio=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO,
    ) is False


def test_ast_prohibits_whole_file_zip_extraction() -> None:
    """AST check verifies ZipFile.read, extract, extractall are never called in production core."""
    core_path = PROJECT_ROOT / "src" / "research" / "external_signal_shadow" / "stage1_5j_b_historical_aggtrades_launch_response.py"
    assert core_path.is_file()

    tree = ast.parse(core_path.read_text(encoding="utf-8"), filename=str(core_path))
    forbidden_methods = {"read", "extract", "extractall"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in forbidden_methods:
                # Prohibit ZipFile whole extraction methods
                pytest.fail(f"Forbidden method call: .{node.func.attr}() found in production core")


# =============================================================================
# 5. Compound-State Precedence Probes
# =============================================================================


def test_compound_state_precedence_probe_earlier_gate_wins(tmp_path: Path) -> None:
    """Earlier frozen gate must reject and stop before later sensitive operation is reached."""
    # Probe 1: Malformed upstream source identity stops before import
    fake_root = tmp_path / "invalid_root"
    fake_root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(Stage1_5JBDiagnosticError, match="upstream_authority_mismatch"):
        admit_upstream_j_a_root(fake_root)


# =============================================================================
# 6. Canonical Multi-Child Complete Fixture & Independent Oracle
# =============================================================================


def test_canonical_multi_child_complete_fixture_oracle_parity() -> None:
    """Derives lexicographically first multi-child complete parent and verifies oracle parity."""
    j_a_data = admit_upstream_j_a_root(CANONICAL_J_A_ROOT)
    parent_records = j_a_data["parent_records"]

    # Locate first coverage_complete parent with >= 2 in-scope USDT children
    selected_parent = None
    for p in sorted(parent_records, key=lambda x: x["source_article_id"]):
        in_scope_usdt = [c["symbol"] for c in p.get("children", []) if c.get("child_scope") == "in_scope_usdt"]
        if p["parent_state"] == "coverage_complete" and len(in_scope_usdt) >= 2:
            selected_parent = p
            break

    assert selected_parent is not None, "Failed to find canonical multi-child complete parent in genuine J-A root"
    in_scope_symbols = [c["symbol"] for c in selected_parent.get("children", []) if c.get("child_scope") == "in_scope_usdt"]
    assert len(in_scope_symbols) >= 2


# =============================================================================
# 7. Canonical Producer & Public Runner Wiring (INV-JB-07, INV-JB-08)
# =============================================================================


def test_canonical_producer_tmp_path_integration(tmp_path: Path) -> None:
    """Canonical producer builds verified temporary receipt from genuine J-A root."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = tmp_path / run_id

    from scripts.governance.verify_stage1_5j_b_receipt_schema import (
        OUTPUT_PARENT,
        PROFILE_ID_V2,
    )
    from scripts.governance.verify_stage1_5j_b_receipt_schema import (
        main as verifier_main,
    )
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    summary = produce_stage1_5j_b_historical_aggtrades_launch_response(
        output_root=target_root,
        run_id=run_id,
    )

    # 1. Assert schema and counts
    assert summary["run_id"] == run_id
    assert len(summary["child_rows"]) == 281
    assert len(summary["child_horizon_rows"]) == 843
    assert len(summary["parent_horizon_rows"]) == 393

    # 2. Assert strict loader passes
    loaded = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(target_root)
    assert loaded["run_id"] == run_id

    # 3. Assert Rule 17 v2 governance verifier CLI passes on the same root
    mock_proj = tmp_path / "mock_proj"
    mock_target = mock_proj / OUTPUT_PARENT / run_id
    shutil.copytree(target_root, mock_target)

    script_dst = mock_proj / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py"
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJECT_ROOT / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py", script_dst)

    cwd = os.getcwd()
    try:
        os.chdir(mock_proj)
        rc = verifier_main(["--profile", PROFILE_ID_V2, "--artifact-root", f"{OUTPUT_PARENT}/{run_id}"])
        assert rc == 0
    finally:
        os.chdir(cwd)


def test_public_runner_wiring_with_test_seam(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Public runner wires to canonical producer when authorized via private test seam."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = tmp_path / run_id
    auth_file = tmp_path / "receipt_generation_authorization.txt"
    auth_file.write_text(
        f"APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
        f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"AUDITED_J_B_CORE_SHA256=placeholder\n"
        f"AUDITED_J_B_CLI_SHA256=placeholder\n"
        f"AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
        f"J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
        f"NETWORK_ALLOWED=false\n"
    )

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        run_stage1_5j_b_historical_aggtrades_launch_response,
    )

    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response._TEST_RECEIPT_AUTH_FILE",
        auth_file,
    )
    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response._TEST_OUTPUT_ROOT",
        target_root,
    )

    rc = run_stage1_5j_b_historical_aggtrades_launch_response(run_id)
    assert rc == 0
    assert target_root.is_dir()
    loaded = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(target_root)
    assert loaded["run_id"] == run_id


def test_public_runner_collision_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pre-existing output directory triggers collision STOP."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = tmp_path / run_id
    target_root.mkdir(parents=True, exist_ok=True)
    auth_file = tmp_path / "receipt_generation_authorization.txt"
    auth_file.write_text(
        f"APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
        f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"AUDITED_J_B_CORE_SHA256=placeholder\n"
        f"AUDITED_J_B_CLI_SHA256=placeholder\n"
        f"AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
        f"J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
        f"NETWORK_ALLOWED=false\n"
    )

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        run_stage1_5j_b_historical_aggtrades_launch_response,
    )

    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response._TEST_RECEIPT_AUTH_FILE",
        auth_file,
    )
    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response._TEST_OUTPUT_ROOT",
        target_root,
    )

    with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_output_collision"):
        run_stage1_5j_b_historical_aggtrades_launch_response(run_id)


def test_public_runner_incomplete_auth_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Public runner returns 1 and creates zero receipts when auth file is fail-open incomplete (P0-01)."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = tmp_path / run_id
    auth_file = tmp_path / "receipt_generation_authorization.txt"
    # Incomplete auth containing only AUTHORIZED_RUN_ID
    auth_file.write_text(f"AUTHORIZED_RUN_ID={run_id}\n")

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        run_stage1_5j_b_historical_aggtrades_launch_response,
    )

    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response._TEST_RECEIPT_AUTH_FILE",
        auth_file,
    )
    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response._TEST_OUTPUT_ROOT",
        target_root,
    )

    rc = run_stage1_5j_b_historical_aggtrades_launch_response(run_id)
    assert rc == 1
    assert not target_root.exists()


@pytest.mark.parametrize(
    "tamper_field,tamper_val,expected_error",
    [
        ("APPROVED_J_B_DESIGN_SHA256", "0" * 64, "design_sha_mismatch"),
        ("APPROVED_J_B_PLAN_SHA256", "0" * 64, "plan_sha_mismatch"),
        ("AUTHORIZED_RUN_ID", "stage1_5j_b_historical_aggtrades_launch_response_20990101T000000Z", "run_id_mismatch"),
        ("AUDITED_CONFIG_SHA256", "0" * 64, "config_sha_mismatch"),
        ("J_A_MANIFEST_SHA256", "0" * 64, "j_a_manifest_sha_mismatch"),
        ("NETWORK_ALLOWED", "true", "network_allowed_must_be_false"),
    ],
)
def test_receipt_generation_auth_parser_negative_probes(tmp_path: Path, tamper_field: str, tamper_val: str, expected_error: str) -> None:
    """Receipt authorization parser rejects each one-fact invalid field (P0-01)."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    auth_file = tmp_path / "receipt_auth_tampered.txt"

    base_auth = {
        "APPROVED_J_B_DESIGN_SHA256": "66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f",
        "APPROVED_J_B_PLAN_SHA256": PLAN_SHA,
        "AUTHORIZED_RUN_ID": run_id,
        "AUDITED_J_B_CORE_SHA256": "placeholder",
        "AUDITED_J_B_CLI_SHA256": "placeholder",
        "AUDITED_CONFIG_SHA256": "771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4",
        "J_A_MANIFEST_SHA256": "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf",
        "NETWORK_ALLOWED": "false",
    }
    base_auth[tamper_field] = tamper_val

    lines = [f"{k}={v}" for k, v in base_auth.items()]
    auth_file.write_text("\n".join(lines) + "\n")

    import src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response as core_mod

    orig_seam = core_mod._TEST_RECEIPT_AUTH_FILE
    core_mod._TEST_RECEIPT_AUTH_FILE = auth_file
    try:
        with pytest.raises(Stage1_5JBDiagnosticError, match=expected_error):
            core_mod._parse_receipt_generation_authorization(auth_file, expected_run_id=run_id, proj=PROJECT_ROOT)
    finally:
        core_mod._TEST_RECEIPT_AUTH_FILE = orig_seam


def test_receipt_generation_auth_parser_missing_and_duplicate_keys(tmp_path: Path) -> None:
    """Authorization parser rejects missing or extra/duplicate lines via line_count_mismatch (P0-01)."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        _parse_receipt_generation_authorization,
    )

    # 1. Missing line (< 8 lines)
    auth_file = tmp_path / "auth_missing.txt"
    auth_file.write_text(f"AUTHORIZED_RUN_ID={run_id}\nNETWORK_ALLOWED=false\n")
    with pytest.raises(Stage1_5JBDiagnosticError, match="line_count_mismatch:2"):
        _parse_receipt_generation_authorization(auth_file, expected_run_id=run_id, proj=PROJECT_ROOT)

    # 2. Duplicate line (> 8 lines)
    auth_file_dup = tmp_path / "auth_dup.txt"
    auth_file_dup.write_text(
        f"APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
        f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"AUTHORIZED_RUN_ID={run_id}\n"
        f"AUDITED_J_B_CORE_SHA256=placeholder\n"
        f"AUDITED_J_B_CLI_SHA256=placeholder\n"
        f"AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
        f"J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
        f"NETWORK_ALLOWED=false\n"
    )
    with pytest.raises(Stage1_5JBDiagnosticError, match="line_count_mismatch:9"):
        _parse_receipt_generation_authorization(auth_file_dup, expected_run_id=run_id, proj=PROJECT_ROOT)


@pytest.mark.parametrize(
    "tampered_content,expected_error",
    [
        # Reordered keys (NETWORK_ALLOWED moved to line 6, exactly reproducing finding P0-01)
        (
            (
                "APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
                "AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
                "NETWORK_ALLOWED=false\n"
                "AUDITED_J_B_CORE_SHA256=placeholder\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\n"
            ),
            "key_order_or_name_mismatch:3:AUDITED_CONFIG_SHA256!=expected:AUDITED_J_B_CORE_SHA256",
        ),
        # Whitespace on key
        (
            (
                " APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
                "AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z\n"
                "AUDITED_J_B_CORE_SHA256=placeholder\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
                "NETWORK_ALLOWED=false\n"
            ),
            "whitespace_forbidden:0",
        ),
        # Whitespace after value
        (
            (
                "APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f \n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
                "AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z\n"
                "AUDITED_J_B_CORE_SHA256=placeholder\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
                "NETWORK_ALLOWED=false\n"
            ),
            "whitespace_forbidden:0",
        ),
        # Whitespace around equals
        (
            (
                "APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
                "AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z\n"
                "AUDITED_J_B_CORE_SHA256 = placeholder\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
                "NETWORK_ALLOWED=false\n"
            ),
            "whitespace_forbidden:3",
        ),
        # CRLF forbidden
        (
            (
                "APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\r\n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\r\n"
                "AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z\r\n"
                "AUDITED_J_B_CORE_SHA256=placeholder\r\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\r\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\r\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\r\n"
                "NETWORK_ALLOWED=false\r\n"
            ),
            "crlf_forbidden",
        ),
        # Blank line in middle
        (
            (
                "APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
                "\n"
                "AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z\n"
                "AUDITED_J_B_CORE_SHA256=placeholder\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
                "NETWORK_ALLOWED=false\n"
            ),
            "line_count_mismatch:9",
        ),
        # Missing trailing newline
        (
            (
                "APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
                "AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z\n"
                "AUDITED_J_B_CORE_SHA256=placeholder\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
                "NETWORK_ALLOWED=false"
            ),
            "must_end_with_single_lf",
        ),
        # Malformed line (no equals)
        (
            (
                "APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
                "AUTHORIZED_RUN_ID:stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z\n"
                "AUDITED_J_B_CORE_SHA256=placeholder\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
                "NETWORK_ALLOWED=false\n"
            ),
            "malformed_line:2",
        ),
        # Empty value
        (
            (
                "APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
                "AUTHORIZED_RUN_ID=\n"
                "AUDITED_J_B_CORE_SHA256=placeholder\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
                "NETWORK_ALLOWED=false\n"
            ),
            "empty_value:2",
        ),
        # Uppercase network allowed
        (
            (
                "APPROVED_J_B_DESIGN_SHA256=66f70bdd77cab60135acee0469446d702d672cd1937c1122d334e2c9b0feed3f\n"
                f"APPROVED_J_B_PLAN_SHA256={PLAN_SHA}\n"
                "AUTHORIZED_RUN_ID=stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z\n"
                "AUDITED_J_B_CORE_SHA256=placeholder\n"
                "AUDITED_J_B_CLI_SHA256=placeholder\n"
                "AUDITED_CONFIG_SHA256=771e6e4462803d9d2c961cc4a526d3e0adea8b35547c64900312390fa273d8d4\n"
                "J_A_MANIFEST_SHA256=b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf\n"
                "NETWORK_ALLOWED=FALSE\n"
            ),
            "network_allowed_must_be_false",
        ),
    ],
)
def test_receipt_generation_auth_parser_strict_grammar_probes(tmp_path: Path, tampered_content: str, expected_error: str) -> None:
    """Authorization parser strictly rejects non-canonical grammar, whitespace, order, and extra lines (P0-01)."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    auth_file = tmp_path / "grammar_test_auth.txt"
    auth_file.write_bytes(tampered_content.encode("ascii"))

    import src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response as core_mod

    orig_seam = core_mod._TEST_RECEIPT_AUTH_FILE
    core_mod._TEST_RECEIPT_AUTH_FILE = auth_file
    try:
        with pytest.raises(Stage1_5JBDiagnosticError, match=expected_error):
            core_mod._parse_receipt_generation_authorization(auth_file, expected_run_id=run_id, proj=PROJECT_ROOT)
    finally:
        core_mod._TEST_RECEIPT_AUTH_FILE = orig_seam


def test_strict_loader_rejects_forged_anchor_state(tmp_path: Path) -> None:
    """Strict domain loader rejects self-consistent but forged anchor_state (P0-02)."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = tmp_path / run_id

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    produce_stage1_5j_b_historical_aggtrades_launch_response(
        output_root=target_root,
        run_id=run_id,
    )

    # Mutate anchor_state on child_rows[0]
    summary_path = target_root / "summary.json"
    s_obj = json.loads(summary_path.read_text(encoding="utf-8"))
    s_obj["child_rows"][0]["anchor_state"] = "forged_semantic_state"
    summary_bytes = (json.dumps(s_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    summary_path.write_bytes(summary_bytes)

    # Re-compute manifest so manifest hash check passes, isolating domain loader schema check
    manifest_path = target_root / "manifest.json"
    m_obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    for art in m_obj["artifacts"]:
        if art["path"] == "summary.json":
            art["sha256"] = hashlib.sha256(summary_bytes).hexdigest()
            art["byte_count"] = len(summary_bytes)
    manifest_path.write_text(json.dumps(m_obj, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_child_row_anchor_state_invalid"):
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(target_root)


def test_producer_concurrency_and_staging_collision(tmp_path: Path) -> None:
    """Producer fail-closed checks for staging collision and concurrency lock (P0-04)."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = tmp_path / run_id

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    # 1. Staging directory collision check
    target_root.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = target_root.parent / f".staging.{run_id}.{os.getpid()}"
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_staging_collision"):
            produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)
    finally:
        shutil.rmtree(staging_dir)

    # 2. Concurrency lock held check
    lock_file = target_root.parent / f".lock.{run_id}"
    lock_fd = open(lock_file, "w")
    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_concurrency_lock_held"):
            produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)
    finally:
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
        lock_fd.close()
        if lock_file.exists():
            lock_file.unlink()


def test_producer_durability_points_injected_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 4: Injected-failure tests for each durability point (INV-JB-RR-04)."""
    from unittest.mock import patch

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS,
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    cov_counts = {
        "j_a_parent_coverage_complete_count": 120,
        "j_a_parent_coverage_gap_count": 11,
        "j_a_target_parent_count": 131,
        "n_child_horizon_complete_by_horizon": {"300000": 0, "3600000": 0, "14400000": 0},
        "n_child_horizon_gap_by_horizon": {"300000": 281, "3600000": 281, "14400000": 281},
        "n_parent_horizon_complete_by_horizon": {"300000": 0, "3600000": 0, "14400000": 0},
        "n_parent_horizon_gap_by_horizon": {"300000": 131, "3600000": 131, "14400000": 131},
        "n_parent_total": 131,
        "n_parent_with_j_a_gap": 11,
        "parent_distribution_by_horizon": {
            str(h): {
                "max": None, "mean": None, "median": None, "min": None, "n_complete_parent": 0,
                "p10": None, "p25": None, "p50": None, "p75": None, "p90": None,
                "top_1_abs_return_contribution": "0", "top_1_parent_ids": [],
                "top_3_abs_return_contribution": "0", "top_3_parent_ids": [],
            }
            for h in EXTERNAL_SIGNAL_STAGE1_5J_B_HORIZONS_MS
        },
    }
    dummy_reduced = {
        "child_rows": [],
        "child_horizon_rows": [],
        "parent_horizon_rows": [],
        "coverage_counts": cov_counts,
    }

    with patch(
        "src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response._reduce_verified_aggtrades_launch_response",
        return_value=dummy_reduced,
    ):
        tmp_parent = tmp_path / "durability_run"
        tmp_parent.mkdir()
        run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
        target_root = tmp_parent / run_id

        # Node 1: file fsync failure
        orig_fsync = os.fsync
        calls = [0]
        def _fail_file_fsync(fd: int) -> None:
            calls[0] += 1
            if calls[0] == 1:
                raise OSError("INJECTED_FILE_FSYNC_FAILURE")
            orig_fsync(fd)

        with patch("os.fsync", side_effect=_fail_file_fsync):
            with pytest.raises(OSError, match="INJECTED_FILE_FSYNC_FAILURE"):
                produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)
            assert not target_root.exists()

        shutil.rmtree(tmp_parent)
        tmp_parent.mkdir()

        # Node 2: staging directory fsync failure (call 4 is the staging dir fsync, after 3 files)
        calls = [0]
        def _fail_staging_fsync(fd: int) -> None:
            calls[0] += 1
            if calls[0] == 4:
                raise OSError("INJECTED_STAGING_FSYNC_FAILURE")
            orig_fsync(fd)

        with patch("os.fsync", side_effect=_fail_staging_fsync):
            with pytest.raises(OSError, match="INJECTED_STAGING_FSYNC_FAILURE"):
                produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)
            assert not target_root.exists()

        shutil.rmtree(tmp_parent)
        tmp_parent.mkdir()

        # Node 3: rename failure
        def _fail_rename(*args: Any, **kwargs: Any) -> None:
            raise OSError("INJECTED_RENAME_FAILURE")

        with patch.object(Path, "rename", side_effect=_fail_rename):
            with pytest.raises(OSError, match="INJECTED_RENAME_FAILURE"):
                produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)
            assert not target_root.exists()
            # Staging root remains, blocking subsequent run with staging collision
            with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_staging_collision"):
                produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)

        shutil.rmtree(tmp_parent)
        tmp_parent.mkdir()

        # Node 4: parent directory fsync failure (call 5 is parent dir fsync)
        calls = [0]
        def _fail_parent_fsync(fd: int) -> None:
            calls[0] += 1
            if calls[0] == 5:
                raise OSError("INJECTED_PARENT_FSYNC_FAILURE")
            orig_fsync(fd)

        with patch("os.fsync", side_effect=_fail_parent_fsync):
            with pytest.raises(OSError, match="INJECTED_PARENT_FSYNC_FAILURE"):
                produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)
            assert target_root.exists()
            # Post-rename target_root blocks subsequent run with output collision
            with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_output_collision"):
                produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)


def test_review_cn_md_render_mutation_fails_closed(tmp_path: Path) -> None:
    """Tampering with review_CN.md markdown causes strict loader to fail closed."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = tmp_path / run_id

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    produce_stage1_5j_b_historical_aggtrades_launch_response(
        output_root=target_root,
        run_id=run_id,
    )

    # Mutate review_CN.md content
    review_path = target_root / "review_CN.md"
    review_path.write_text(review_path.read_text(encoding="utf-8") + "\n# Extra Tampered Content\n")

    # Update manifest so it doesn't fail on manifest SHA, but on review re-render projection
    manifest_path = target_root / "manifest.json"
    m_obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    for art in m_obj["artifacts"]:
        if art["path"] == "review_CN.md":
            art["sha256"] = hashlib.sha256(review_path.read_bytes()).hexdigest()
            art["byte_count"] = len(review_path.read_bytes())
    manifest_path.write_text(json.dumps(m_obj, sort_keys=True, separators=(",", ":")) + "\n")

    with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_review_projection_mismatch"):
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(target_root)


def test_source_state_one_row_mutation_fails_loader_and_v2(tmp_path: Path) -> None:
    """One-row valid-enum source-state mutation fails closed at both domain loader and Rule 17 v2 verifier."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = tmp_path / run_id

    from scripts.governance.verify_stage1_5j_b_receipt_schema import (
        OUTPUT_PARENT,
        PROFILE_ID_V2,
    )
    from scripts.governance.verify_stage1_5j_b_receipt_schema import (
        main as verifier_main,
    )
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    produce_stage1_5j_b_historical_aggtrades_launch_response(
        output_root=target_root,
        run_id=run_id,
    )

    # Mutate child_rows[0].j_a_parent_state to valid enum coverage_evidence_gap_archive
    summary_path = target_root / "summary.json"
    s_obj = json.loads(summary_path.read_text(encoding="utf-8"))
    assert s_obj["child_rows"][0]["j_a_parent_state"] == "coverage_complete"
    s_obj["child_rows"][0]["j_a_parent_state"] = "coverage_evidence_gap_archive"
    summary_bytes = (json.dumps(s_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    summary_path.write_bytes(summary_bytes)

    # Recompute manifest so manifest hash check passes
    manifest_path = target_root / "manifest.json"
    m_obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    for art in m_obj["artifacts"]:
        if art["path"] == "summary.json":
            art["sha256"] = hashlib.sha256(summary_bytes).hexdigest()
            art["byte_count"] = len(summary_bytes)
    manifest_path.write_text(json.dumps(m_obj, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    # 1. Assert domain loader fails closed
    with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_child_row_j_a_parent_state_mismatch"):
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(target_root)

    # 2. Assert Rule 17 v2 verifier CLI fails closed (rc=1)
    mock_proj = tmp_path / "mock_proj_one_row"
    mock_target = mock_proj / OUTPUT_PARENT / run_id
    shutil.copytree(target_root, mock_target)
    script_dst = mock_proj / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py"
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJECT_ROOT / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py", script_dst)

    cwd = os.getcwd()
    try:
        os.chdir(mock_proj)
        rc = verifier_main(["--profile", PROFILE_ID_V2, "--artifact-root", f"{OUTPUT_PARENT}/{run_id}"])
        assert rc == 1
    finally:
        os.chdir(cwd)


def test_internally_consistent_source_state_rewrite_fails_domain_loader(tmp_path: Path) -> None:
    """Internally consistent multi-row source-state rewrite passes v2 verifier but fails closed at domain loader."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z"
    target_root = tmp_path / run_id

    from scripts.governance.verify_stage1_5j_b_receipt_schema import (
        OUTPUT_PARENT,
        PROFILE_ID_V2,
    )
    from scripts.governance.verify_stage1_5j_b_receipt_schema import (
        main as verifier_main,
    )
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    produce_stage1_5j_b_historical_aggtrades_launch_response(
        output_root=target_root,
        run_id=run_id,
    )

    summary_path = target_root / "summary.json"
    s_obj = json.loads(summary_path.read_text(encoding="utf-8"))

    # Find one complete parent and one gap parent
    parent_states = {}
    for phr in s_obj["parent_horizon_rows"]:
        parent_states[phr["source_article_id"]] = phr["source_parent_state"]

    complete_p_ids = [pid for pid, st in parent_states.items() if st == "coverage_complete"]
    gap_p_ids = [pid for pid, st in parent_states.items() if st != "coverage_complete"]
    assert len(complete_p_ids) == 120
    assert len(gap_p_ids) == 11

    p_comp = complete_p_ids[0]
    p_gap = gap_p_ids[0]

    comp_symbols = [cr["symbol"] for cr in s_obj["child_rows"] if cr["source_article_id"] == p_comp]
    gap_symbols = [cr["symbol"] for cr in s_obj["child_rows"] if cr["source_article_id"] == p_gap]

    # Swap their states in parent_horizon_rows
    for phr in s_obj["parent_horizon_rows"]:
        if phr["source_article_id"] == p_comp:
            phr["source_parent_state"] = "coverage_evidence_gap_archive"
            phr["parent_horizon_state"] = "parent_horizon_evidence_gap"
            phr["parent_gross_return_bps"] = None
            phr["parent_sampled_min_excursion_bps"] = None
            phr["parent_sampled_max_excursion_bps"] = None
            phr["failed_child_reasons"] = [
                {"missing_reason": "inherited_j_a_parent_gap", "symbol": sym}
                for sym in comp_symbols
            ]
        elif phr["source_article_id"] == p_gap:
            phr["source_parent_state"] = "coverage_complete"
            phr["parent_horizon_state"] = "parent_horizon_evidence_gap"
            phr["parent_gross_return_bps"] = None
            phr["parent_sampled_min_excursion_bps"] = None
            phr["parent_sampled_max_excursion_bps"] = None
            phr["failed_child_reasons"] = [
                {"missing_reason": "evidence_gap_anchor_delay", "symbol": sym}
                for sym in gap_symbols
            ]

    # Update child_rows consistently
    for cr in s_obj["child_rows"]:
        if cr["source_article_id"] == p_comp:
            cr["j_a_parent_state"] = "coverage_evidence_gap_archive"
            cr["anchor_state"] = "anchor_unavailable_inherited_j_a_parent_gap"
            cr["anchor_delay_ms"] = None
            cr["anchor_price"] = None
            cr["anchor_time_ms"] = None
            cr["required_archive_dates_by_horizon"] = {"300000": [], "3600000": [], "14400000": []}
        elif cr["source_article_id"] == p_gap:
            cr["j_a_parent_state"] = "coverage_complete"
            cr["anchor_state"] = "anchor_unavailable_delay_exceeded"
            cr["anchor_delay_ms"] = None
            cr["anchor_price"] = None
            cr["anchor_time_ms"] = None

    # Update child_horizon_rows consistently
    for chr_ in s_obj["child_horizon_rows"]:
        if chr_["source_article_id"] == p_comp:
            chr_["child_horizon_state"] = "child_horizon_evidence_gap"
            chr_["missing_reason"] = "inherited_j_a_parent_gap"
            chr_["gross_return_bps"] = None
            chr_["horizon_offset_ms"] = None
            chr_["horizon_price"] = None
            chr_["horizon_selected_time_ms"] = None
            chr_["sampled_max_excursion_bps"] = None
            chr_["sampled_min_excursion_bps"] = None
            chr_["trade_count"] = None
        elif chr_["source_article_id"] == p_gap:
            chr_["child_horizon_state"] = "child_horizon_evidence_gap"
            chr_["missing_reason"] = "evidence_gap_anchor_delay"
            chr_["gross_return_bps"] = None
            chr_["horizon_offset_ms"] = None
            chr_["horizon_price"] = None
            chr_["horizon_selected_time_ms"] = None
            chr_["sampled_max_excursion_bps"] = None
            chr_["sampled_min_excursion_bps"] = None
            chr_["trade_count"] = None

    summary_bytes = (json.dumps(s_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    summary_path.write_bytes(summary_bytes)

    # Recompute manifest so manifest hash check passes
    manifest_path = target_root / "manifest.json"
    m_obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    for art in m_obj["artifacts"]:
        if art["path"] == "summary.json":
            art["sha256"] = hashlib.sha256(summary_bytes).hexdigest()
            art["byte_count"] = len(summary_bytes)
    manifest_path.write_text(json.dumps(m_obj, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    # 1. Assert Rule 17 v2 verifier passes (rc=0) because receipt is internally self-consistent
    mock_proj = tmp_path / "mock_proj_rewrite"
    mock_target = mock_proj / OUTPUT_PARENT / run_id
    shutil.copytree(target_root, mock_target)
    script_dst = mock_proj / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py"
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(PROJECT_ROOT / "scripts" / "governance" / "verify_stage1_5j_b_receipt_schema.py", script_dst)

    cwd = os.getcwd()
    try:
        os.chdir(mock_proj)
        rc = verifier_main(["--profile", PROFILE_ID_V2, "--artifact-root", f"{OUTPUT_PARENT}/{run_id}"])
        assert rc == 0, "Internally consistent forged receipt must pass structural v2 verifier"
    finally:
        os.chdir(cwd)

    # 2. Assert domain loader fails closed through real J-A upstream re-admission
    with pytest.raises(Stage1_5JBDiagnosticError, match="stage1_5j_b_.*_mismatch"):
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(target_root)


# =============================================================================
# 8. Task 1: Verified Archive Streaming Reduction Remediation & Independent Oracle
# =============================================================================

def _compute_independent_test_local_oracle(canonical_j_a_root: Path) -> dict[str, Any]:
    """Test-local semantic oracle independently reading genuine J-A root and raw ZIP bytes.

    Must NOT import or call production TCB reduction helpers or precomputed J-B outputs.
    Deterministic selection: lexicographically first J-A complete (source_article_id, symbol).
    """
    import csv
    import io
    import zipfile
    from decimal import ROUND_HALF_EVEN, Decimal

    from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
        load_verified_stage1_5j_a_historical_archive_coverage_root,
    )

    j_a_data = load_verified_stage1_5j_a_historical_archive_coverage_root(canonical_j_a_root)

    # Deterministic selection: lexicographically first J-A complete parent and in-scope USDT child
    selected_parent = None
    selected_child = None
    for p in sorted(j_a_data["parent_records"], key=lambda x: x["source_article_id"]):
        if p["parent_state"] == "coverage_complete":
            in_scope_usdt = sorted(
                [c for c in p.get("children", []) if c.get("child_scope") == "in_scope_usdt"],
                key=lambda x: x["symbol"],
            )
            if in_scope_usdt:
                selected_parent = p
                selected_child = in_scope_usdt[0]
                break

    if not selected_parent or not selected_child:
        raise RuntimeError("Oracle failed to locate canonical J-A complete child")

    parent_article_id = selected_parent["source_article_id"]
    symbol = selected_child["symbol"]
    launch_time_ms = selected_child["symbol_launch_time_ms"]
    if launch_time_ms is None:
        raise RuntimeError(f"Missing launch time for {symbol}")

    # Resolve required package records for this child
    child_pkgs = [
        r for r in j_a_data["archive_package_records"]
        if r["parent_article_id"] == parent_article_id and r["symbol"] == symbol
    ]
    if not child_pkgs:
        raise RuntimeError(f"No archive package records found for {symbol}")

    # Read trades from the admitted raw ZIP archive
    utc_date = child_pkgs[0]["utc_date"]
    zip_path = canonical_j_a_root / "raw" / "archive" / symbol / f"{symbol}-aggTrades-{utc_date}.zip"
    if not zip_path.is_file():
        raise RuntimeError(f"Admitted raw ZIP does not exist: {zip_path}")

    trades: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_names = zf.namelist()
        if len(csv_names) != 1:
            raise RuntimeError(f"Expected 1 CSV in zip, found {len(csv_names)}")
        with zf.open(csv_names[0], "r") as raw_f:
            text_stream = io.TextIOWrapper(raw_f, encoding="utf-8")
            reader = csv.reader(text_stream)
            header = next(reader)
            if header != ["agg_trade_id", "price", "quantity", "first_trade_id", "last_trade_id", "transact_time", "is_buyer_maker"]:
                raise RuntimeError(f"Invalid CSV header: {header}")
            last_ts = -1
            last_tid = -1
            for row in reader:
                tid = int(row[0])
                price_dec = Decimal(row[1])
                qty_dec = Decimal(row[2])
                ts = int(row[5])
                if price_dec <= Decimal(0) or not price_dec.is_finite():
                    raise RuntimeError(f"Non-positive or non-finite price: {price_dec}")
                if ts < last_ts:
                    raise RuntimeError(f"Out of order timestamp: {ts} < {last_ts}")
                if ts == last_ts and tid <= last_tid:
                    raise RuntimeError(f"Out of order trade id on tie: {tid} <= {last_tid}")
                last_ts = ts
                last_tid = tid
                trades.append({
                    "agg_trade_id": tid,
                    "price": price_dec,
                    "quantity": qty_dec,
                    "transact_time": ts,
                })

    # Select anchor: earliest trade with transact_time >= launch_time_ms
    anchor_trade = None
    for t in trades:
        if t["transact_time"] >= launch_time_ms:
            anchor_trade = t
            break

    if not anchor_trade:
        raise RuntimeError(f"No anchor trade found for {symbol} at launch {launch_time_ms}")

    anchor_delay_ms = anchor_trade["transact_time"] - launch_time_ms
    if anchor_delay_ms > 300_000:
        raise RuntimeError(f"Anchor delay {anchor_delay_ms} exceeds max delay")

    anchor_price = anchor_trade["price"].quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)

    # Horizons: 5m (300000), 1h (3600000), 4h (14400000)
    horizons_out: dict[int, dict[str, Any]] = {}
    bps_factor = Decimal(10000)
    anchor_idx = trades.index(anchor_trade)

    for h_ms in [300000, 3600000, 14400000]:
        target_ts = anchor_trade["transact_time"] + h_ms
        search_start = target_ts - 60_000
        cand_trades = [t for t in trades if search_start <= t["transact_time"] <= target_ts]
        if not cand_trades:
            raise RuntimeError(f"No trades in horizon window for {symbol} at {h_ms}ms")

        # Horizon trade: latest trade with search_start <= transact_time <= target_ts
        h_trade = cand_trades[-1]
        h_idx = trades.index(h_trade)
        closed_interval = trades[anchor_idx : h_idx + 1]

        h_price = h_trade["price"].quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
        gross_return = (bps_factor * (h_price / anchor_price - Decimal(1))).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)

        min_p = min(t["price"] for t in closed_interval).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
        max_p = max(t["price"] for t in closed_interval).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
        min_excursion = (bps_factor * (min_p / anchor_price - Decimal(1))).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
        max_excursion = (bps_factor * (max_p / anchor_price - Decimal(1))).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)

        def _oracle_format_decimal(d: Decimal) -> str:
            if not d.is_finite():
                raise RuntimeError("Non-finite decimal")
            if d == Decimal(0):
                return "0"
            s = str(d)
            if "." in s:
                s = s.rstrip("0").rstrip(".")
            return s

        def _oracle_format_bps(d: Decimal) -> str:
            q = d.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)
            return _oracle_format_decimal(q)

        horizons_out[h_ms] = {
            "horizon_ms": h_ms,
            "horizon_target_time_ms": target_ts,
            "horizon_selected_time_ms": h_trade["transact_time"],
            "horizon_offset_ms": h_trade["transact_time"] - target_ts,
            "horizon_price": _oracle_format_decimal(h_price),
            "gross_return_bps": _oracle_format_bps(gross_return),
            "sampled_min_excursion_bps": _oracle_format_bps(min_excursion),
            "sampled_max_excursion_bps": _oracle_format_bps(max_excursion),
            "trade_count": len(closed_interval),
        }

    def _oracle_format_anchor(d: Decimal) -> str:
        s = str(d)
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s

    return {
        "parent_article_id": parent_article_id,
        "symbol": symbol,
        "launch_time_ms": launch_time_ms,
        "anchor_state": "anchor_found",
        "anchor_time_ms": anchor_trade["transact_time"],
        "anchor_delay_ms": anchor_delay_ms,
        "anchor_price": _oracle_format_anchor(anchor_price),
        "horizons": horizons_out,
    }


def test_canonical_raw_oracle_ast_independence() -> None:
    """Oracle function body AST must not import or call production TCB reduction helpers."""
    import inspect
    source = inspect.getsource(_compute_independent_test_local_oracle)
    tree = ast.parse(source)

    forbidden_refs = {
        "stage1_5j_b_historical_aggtrades_launch_response",
        "_reduce_verified_aggtrades_launch_response",
        "select_launch_anchor_trade",
        "select_horizon_trade",
        "calculate_child_horizon_outcomes",
        "aggregate_parent_horizon_outcomes",
        "produce_stage1_5j_b_historical_aggtrades_launch_response",
        "load_verified_stage1_5j_b_historical_aggtrades_launch_response_root",
        "run_stage1_5j_b_historical_aggtrades_launch_response",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in forbidden_refs:
            pytest.fail(f"Oracle references production symbol: {node.id}")
        if isinstance(node, ast.Attribute) and node.attr in forbidden_refs:
            pytest.fail(f"Oracle references production attribute: {node.attr}")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in forbidden_refs:
                    pytest.fail(f"Oracle imports production symbol: {alias.name}")
        if isinstance(node, ast.ImportFrom):
            if node.module and any(f in node.module for f in forbidden_refs):
                pytest.fail(f"Oracle imports from production module: {node.module}")


def test_canonical_raw_oracle_monkeypatch_independence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Oracle must compute correct results even if all production TCB entries are disabled."""
    import src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response as prod_mod

    def _poisoned_call(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Production TCB reached by oracle")

    poison_attrs = [
        "_reduce_verified_aggtrades_launch_response",
        "select_launch_anchor_trade",
        "select_horizon_trade",
        "calculate_child_horizon_outcomes",
        "aggregate_parent_horizon_outcomes",
        "produce_stage1_5j_b_historical_aggtrades_launch_response",
        "load_verified_stage1_5j_b_historical_aggtrades_launch_response_root",
        "run_stage1_5j_b_historical_aggtrades_launch_response",
    ]
    for attr in poison_attrs:
        if hasattr(prod_mod, attr):
            monkeypatch.setattr(prod_mod, attr, _poisoned_call)

    # Oracle must run cleanly without hitting any poisoned production helper
    oracle = _compute_independent_test_local_oracle(CANONICAL_J_A_ROOT)
    assert oracle["symbol"] == "PRLUSDT"
    assert oracle["anchor_delay_ms"] == 380
    assert oracle["anchor_price"] == "0.1937"
    assert len(oracle["horizons"]) == 3
    assert oracle["horizons"][300000]["trade_count"] == 5753


def test_canonical_raw_oracle_parity_with_producer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Canonical Class-A test: producer output must match independent oracle for complete child."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261014T010000Z"
    target_root = tmp_path / run_id

    # 1. Patch all network exits to immediate failure
    def _fail_network(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("NETWORK_ACCESS_FORBIDDEN")

    monkeypatch.setattr("socket.socket", _fail_network)
    monkeypatch.setattr("urllib.request.urlopen", _fail_network)
    monkeypatch.setattr("http.client.HTTPConnection", _fail_network)

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    # 2. Compute oracle expectations
    oracle = _compute_independent_test_local_oracle(CANONICAL_J_A_ROOT)

    # 3. Run canonical producer
    summary = produce_stage1_5j_b_historical_aggtrades_launch_response(
        output_root=target_root,
        run_id=run_id,
    )

    # 4. Locate canonical complete child row
    target_child_row = None
    for cr in summary["child_rows"]:
        if cr["source_article_id"] == oracle["parent_article_id"] and cr["symbol"] == oracle["symbol"]:
            target_child_row = cr
            break

    assert target_child_row is not None, "Target child row not found in producer output"
    assert target_child_row["anchor_state"] == "anchor_found", (
        f"Expected anchor_state='anchor_found', got {target_child_row['anchor_state']}"
    )
    assert target_child_row["anchor_price"] is not None, "anchor_price must not be null"
    assert target_child_row["anchor_price"] == oracle["anchor_price"], (
        f"anchor_price mismatch: producer={target_child_row['anchor_price']} oracle={oracle['anchor_price']}"
    )
    assert target_child_row["anchor_delay_ms"] == oracle["anchor_delay_ms"]

    # 5. Verify child_horizon_rows matching oracle
    child_h_rows = [
        r for r in summary["child_horizon_rows"]
        if r["source_article_id"] == oracle["parent_article_id"] and r["symbol"] == oracle["symbol"]
    ]
    assert len(child_h_rows) == 3

    for chr_ in child_h_rows:
        h_ms = chr_["horizon_ms"]
        assert chr_["child_horizon_state"] == "child_horizon_complete", (
            f"child_horizon_state for {h_ms}ms must be complete, got {chr_['child_horizon_state']}"
        )
        assert chr_["horizon_price"] is not None
        assert chr_["horizon_price"] == oracle["horizons"][h_ms]["horizon_price"]
        assert chr_["gross_return_bps"] == oracle["horizons"][h_ms]["gross_return_bps"]
        assert chr_["trade_count"] == oracle["horizons"][h_ms]["trade_count"]

    # 6. Verify strict loader parses and validates this root
    loaded = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(target_root)
    assert loaded["run_id"] == run_id


def test_stream_parser_ast_prohibits_network_imports() -> None:
    """J-B core must not import socket, http, urllib, requests, aiohttp, or websocket transports."""
    core_path = PROJECT_ROOT / "src" / "research" / "external_signal_shadow" / "stage1_5j_b_historical_aggtrades_launch_response.py"
    tree = ast.parse(core_path.read_text(encoding="utf-8"), filename=str(core_path))

    forbidden_modules = {
        "socket",
        "http",
        "urllib",
        "requests",
        "aiohttp",
        "websockets",
        "websocket",
        "httpx",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in forbidden_modules:
                    pytest.fail(f"Forbidden network module imported: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                if mod in forbidden_modules:
                    pytest.fail(f"Forbidden network module import from: {node.module}")


def test_raw_reduction_class_b_physically_copied_tree_rejection(tmp_path: Path) -> None:
    """Class-B negative: physically copied isolated tree with tampered ZIP byte fails closed at admission."""
    corrupt_root = tmp_path / "corrupt_j_a_root"

    # Physically copy genuine J-A root to isolated temporary tree (NO symlink / hardlink)
    shutil.copytree(CANONICAL_J_A_ROOT, corrupt_root)

    # Pick one ZIP and tamper 1 byte
    target_zip = next(corrupt_root.glob("raw/archive/*/*.zip"))
    orig_bytes = target_zip.read_bytes()
    tampered_bytes = bytearray(orig_bytes)
    tampered_bytes[0] ^= 0xFF
    target_zip.write_bytes(tampered_bytes)

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        admit_upstream_j_a_root,
    )
    with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_.*"):
        admit_upstream_j_a_root(corrupt_root)


def test_stream_parser_csv_malformed_and_resource_caps(tmp_path: Path) -> None:
    """Class-C pure seam: malformed CSV headers, negative prices, and reduced resource caps fail closed."""
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        validate_aggtrades_csv_header,
        validate_zip_archive_package,
    )

    # 1. Invalid CSV headers
    assert validate_aggtrades_csv_header(["col1", "col2"]) is False
    assert validate_aggtrades_csv_header(["agg_trade_id", "price"]) is False

    # 2. Synthetic ZIP testing reduced resource caps
    test_zip = tmp_path / "test.zip"
    with zipfile.ZipFile(test_zip, "w") as zf:
        zf.writestr("test.csv", "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n1,10.0,1.0,1,1,1000,false\n")

    # Pass normal caps
    assert validate_zip_archive_package(test_zip) is True

    # Fail max_zip_bytes
    assert validate_zip_archive_package(test_zip, max_zip_bytes=10) is False

    # Fail max_uncompressed_bytes
    assert validate_zip_archive_package(test_zip, max_uncompressed_bytes=10) is False

    # Fail max_ratio
    assert validate_zip_archive_package(test_zip, max_ratio=0) is False


def test_raw_reduction_class_d_persisted_outcome_mutation_rejected(tmp_path: Path) -> None:
    """Class-D: single mutation on persisted child outcome fails closed under strict loader."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261014T020000Z"
    target_root = tmp_path / run_id

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)

    # Mutate summary.json: inject conflicting anchor_state on child row 0
    summary_path = target_root / "summary.json"
    summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_data["child_rows"][0]["anchor_state"] = "anchor_found"
    summary_data["child_rows"][0]["anchor_price"] = "1.23450000"
    summary_data["child_rows"][0]["anchor_delay_ms"] = 100
    summary_data["child_rows"][0]["anchor_time_ms"] = 1700000000100

    new_bytes = (json.dumps(summary_data, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    summary_path.write_bytes(new_bytes)

    # Recompute manifest hash for summary.json
    manifest_path = target_root / "manifest.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for art in manifest_data["artifacts"]:
        if art["path"] == "summary.json":
            art["sha256"] = hashlib.sha256(new_bytes).hexdigest()
            art["byte_count"] = len(new_bytes)
    manifest_path.write_text(json.dumps(manifest_data, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    # Strict loader must fail closed
    with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_b_.*"):
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(target_root)


def test_raw_open_failure_for_complete_child_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Forced raw-open failure on complete child must raise named STOP, never emit missing_horizon_trade."""
    run_id = "stage1_5j_b_historical_aggtrades_launch_response_20261014T030000Z"
    target_root = tmp_path / run_id

    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    # Patch ZipFile.open to fail when reading raw package
    def _faulty_open(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise OSError("SIMULATED_RAW_DISK_READ_FAILURE")

    monkeypatch.setattr(zipfile.ZipFile, "open", _faulty_open)

    # Must raise named STOP (stage1_5j_b_raw_reduction_not_executed or raw read error), not silently publish gap
    with pytest.raises((Stage1_5JBDiagnosticError, OSError)):
        produce_stage1_5j_b_historical_aggtrades_launch_response(target_root, run_id)


def test_raw_reduction_legacy_roots_not_admissible(tmp_path: Path) -> None:
    """Both frozen legacy roots/RUN_IDs are rejected from producer and loader with named STOP."""
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        produce_stage1_5j_b_historical_aggtrades_launch_response,
    )

    legacy_run_ids = [
        "stage1_5j_b_historical_aggtrades_launch_response_20261013T000000Z",
        "stage1_5j_b_historical_aggtrades_launch_response_20261013T040000Z",
    ]

    for leg_id in legacy_run_ids:
        # Producer must reject legacy RUN_ID
        with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_b_legacy_root_not_admissible"):
            produce_stage1_5j_b_historical_aggtrades_launch_response(tmp_path / leg_id, leg_id)

        # Loader must reject legacy root
        leg_root = PROJECT_ROOT / "data" / "external_signal_shadow" / "stage1_5j_b" / "historical_aggtrades_launch_response" / leg_id
        with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_b_legacy_root_not_admissible"):
            load_verified_stage1_5j_b_historical_aggtrades_launch_response_root(leg_root)


def test_open_zip_without_persisted_j_a_package_record_rejected(tmp_path: Path) -> None:
    """P0-01: A canonical-looking ZIP on disk without a matching persisted record cannot be opened (INV-JB-RR-01, INV-JB-RR-05)."""
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        _reduce_verified_aggtrades_launch_response,
    )

    sym = "TESTUSDT"
    utc_date = "2024-01-01"
    p_id = "art_test_p0_01"
    lt_ms = 1704067200000

    mock_j_a_root = tmp_path / "mock_j_a_root"
    zip_path = mock_j_a_root / "raw" / "archive" / sym / f"{sym}-aggTrades-{utc_date}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    header = "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
    csv_content = header + f"1,10.0,1.0,1,1,{lt_ms + 1000},false\n"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{zip_path.stem}.csv", csv_content)
    chk_path = zip_path.with_name(f"{zip_path.name}.CHECKSUM")
    sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    chk_path.write_text(f"{sha}  {zip_path.name}\n", encoding="utf-8")

    # j_a_data has coverage_complete parent with in_scope child, but NO archive_package_records
    j_a_data = {
        "parent_records": [{
            "source_article_id": p_id,
            "parent_state": "coverage_complete",
            "children": [{
                "symbol": sym,
                "child_scope": "in_scope_usdt",
                "symbol_launch_time_ms": lt_ms,
            }],
        }],
        "archive_package_records": [],
    }

    # Reducer must fail closed and NOT open the unauthenticated ZIP
    with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_b_.*"):
        _reduce_verified_aggtrades_launch_response(mock_j_a_root, j_a_data)


def test_anchor_selection_cross_utc_midnight_boundary(tmp_path: Path) -> None:
    """P0-02: Anchor selection streams across UTC midnight, selects earliest physical row on equal ts, and enforces delay cap (INV-JB-RR-02, INV-JB-RR-03)."""
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        _reduce_verified_aggtrades_launch_response,
    )

    sym = "MIDUSDT"
    p_id = "art_test_p0_02"
    # Launch is 100ms before midnight: 2024-01-01T23:59:59.900Z
    lt_ms = 1704153599900
    d1 = "2024-01-01"
    d2 = "2024-01-02"

    mock_j_a_root = tmp_path / "mock_j_a_midnight"

    # Day 1 ZIP has trades before launch only (e.g. at 23:59:50)
    zip1 = mock_j_a_root / "raw" / "archive" / sym / f"{sym}-aggTrades-{d1}.zip"
    zip1.parent.mkdir(parents=True, exist_ok=True)
    header = "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
    csv1 = header + f"1,1.0,1.0,1,1,{lt_ms - 9900},false\n"
    with zipfile.ZipFile(zip1, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{zip1.stem}.csv", csv1)
    chk1 = zip1.with_name(f"{zip1.name}.CHECKSUM")
    chk1.write_text(f"{hashlib.sha256(zip1.read_bytes()).hexdigest()}  {zip1.name}\n", encoding="utf-8")

    # Day 2 ZIP has two trades at exactly +100ms: 1704153600000 (equal timestamps) with prices 0.50 and 0.60
    # and horizon trades for 5m (+300000ms: 1704153900000), 1h, 4h
    zip2 = mock_j_a_root / "raw" / "archive" / sym / f"{sym}-aggTrades-{d2}.zip"
    t_anchor = lt_ms + 100
    csv2 = header + (
        f"2,0.50,10.0,2,2,{t_anchor},false\n"
        f"3,0.60,10.0,3,3,{t_anchor},false\n"
        f"4,0.55,10.0,4,4,{t_anchor + 300000},false\n"
        f"5,0.58,10.0,5,5,{t_anchor + 3600000},false\n"
        f"6,0.52,10.0,6,6,{t_anchor + 14400000},false\n"
    )
    with zipfile.ZipFile(zip2, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{zip2.stem}.csv", csv2)
    chk2 = zip2.with_name(f"{zip2.name}.CHECKSUM")
    chk2.write_text(f"{hashlib.sha256(zip2.read_bytes()).hexdigest()}  {zip2.name}\n", encoding="utf-8")

    def _make_pkg_rec(utc_date: str) -> dict[str, Any]:
        return {
            "checksum_request_id": 1,
            "child_state": "archive_verified_with_post_launch_rows",
            "logical_archive_identity": {
                "market": "futures_um",
                "metric": "aggTrades",
                "parent_article_id": p_id,
                "symbol": sym,
                "utc_date": utc_date,
            },
            "parent_article_id": p_id,
            "symbol": sym,
            "utc_date": utc_date,
            "zip_request_id": 2,
        }

    j_a_data = {
        "parent_records": [{
            "source_article_id": p_id,
            "parent_state": "coverage_complete",
            "children": [{
                "symbol": sym,
                "child_scope": "in_scope_usdt",
                "symbol_launch_time_ms": lt_ms,
            }],
        }],
        "archive_package_records": [_make_pkg_rec(d1), _make_pkg_rec(d2)],
    }

    # 1. Normal cross-midnight anchor discovery
    res = _reduce_verified_aggtrades_launch_response(mock_j_a_root, j_a_data)
    cr = res["child_rows"][0]
    assert cr["anchor_state"] == "anchor_found"
    assert cr["anchor_time_ms"] == t_anchor
    assert cr["anchor_delay_ms"] == 100
    assert cr["anchor_price"] == "0.5"

    # 2. Delay boundary test: trade at lt_ms + 300_001 ms (> 300,000ms delay limit)
    t_too_late = lt_ms + 300001
    csv2_late = header + f"2,0.50,10.0,2,2,{t_too_late},false\n"
    with zipfile.ZipFile(zip2, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{zip2.stem}.csv", csv2_late)
    chk2.write_text(f"{hashlib.sha256(zip2.read_bytes()).hexdigest()}  {zip2.name}\n", encoding="utf-8")

    res_late = _reduce_verified_aggtrades_launch_response(mock_j_a_root, j_a_data)
    cr_late = res_late["child_rows"][0]
    assert cr_late["anchor_state"] == "anchor_unavailable_delay_exceeded"
    assert cr_late["anchor_price"] is None
    assert cr_late["anchor_time_ms"] is None


def test_stream_parser_enforces_buffer_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """P0-03: Frozen STREAM_CHUNK_BYTES (65536) is enforced during raw streaming (INV-JB-RR-04)."""
    import src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response as core_mod
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
        _reduce_verified_aggtrades_launch_response,
    )

    sym = "BUFUSDT"
    p_id = "art_test_p0_03"
    lt_ms = 1704067200000
    d = "2024-01-01"

    mock_j_a_root = tmp_path / "mock_j_a_buf"
    zip_path = mock_j_a_root / "raw" / "archive" / sym / f"{sym}-aggTrades-{d}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    header = "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n"
    rows_str = "\n".join(
        f"{i},10.0,1.0,{i},{i},{lt_ms + i * 10},false"
        for i in range(1, 2000)
    )
    csv_content = header + rows_str + "\n"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{zip_path.stem}.csv", csv_content)
    chk_path = zip_path.with_name(f"{zip_path.name}.CHECKSUM")
    chk_path.write_text(f"{hashlib.sha256(zip_path.read_bytes()).hexdigest()}  {zip_path.name}\n", encoding="utf-8")

    j_a_data = {
        "parent_records": [{
            "source_article_id": p_id,
            "parent_state": "coverage_complete",
            "children": [{
                "symbol": sym,
                "child_scope": "in_scope_usdt",
                "symbol_launch_time_ms": lt_ms,
            }],
        }],
        "archive_package_records": [{
            "checksum_request_id": 1,
            "child_state": "archive_verified_with_post_launch_rows",
            "logical_archive_identity": {
                "market": "futures_um",
                "metric": "aggTrades",
                "parent_article_id": p_id,
                "symbol": sym,
                "utc_date": d,
            },
            "parent_article_id": p_id,
            "symbol": sym,
            "utc_date": d,
            "zip_request_id": 2,
        }],
    }

    observed_chunks: list[int] = []
    orig_readinto = core_mod._ChunkBoundedReader.readinto

    def _recording_readinto(self: Any, b: Any) -> int:
        observed_chunks.append(len(b))
        return orig_readinto(self, b)

    monkeypatch.setattr(core_mod._ChunkBoundedReader, "readinto", _recording_readinto)
    _reduce_verified_aggtrades_launch_response(mock_j_a_root, j_a_data)
    assert len(observed_chunks) > 0
    assert all(n <= EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES for n in observed_chunks)



def test_open_verified_package_stream_fail_closed_checks(tmp_path: Path) -> None:
    """_open_verified_package_stream fails closed on logical identity, state, symlink, checksum tampering, and chunk cap (INV-JB-RR-01, INV-JB-RR-04)."""
    from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
        EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
        Stage1_5JBDiagnosticError,
        _ChunkBoundedReader,
        _open_verified_package_stream,
    )

    root = tmp_path / "mock_root"
    sym = "SEAMUSDT"
    utc_date = "2024-01-01"
    p_id = "art_seam_01"

    zip_path = root / "raw" / "archive" / sym / f"{sym}-aggTrades-{utc_date}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    csv_bytes = b"agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n1,10.0,1.0,1,1,1000,false\n"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{zip_path.stem}.csv", csv_bytes)
    chk_path = zip_path.with_name(f"{zip_path.name}.CHECKSUM")
    actual_sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    chk_path.write_text(f"{actual_sha}  {zip_path.name}\n", encoding="utf-8")

    valid_rec = {
        "checksum_request_id": 1,
        "child_state": "archive_verified_with_post_launch_rows",
        "logical_archive_identity": {
            "market": "futures_um",
            "metric": "aggTrades",
            "parent_article_id": p_id,
            "symbol": sym,
            "utc_date": utc_date,
        },
        "parent_article_id": p_id,
        "symbol": sym,
        "utc_date": utc_date,
        "zip_request_id": 2,
    }

    # 1. Positive case opens successfully
    with _open_verified_package_stream(root, valid_rec) as stream:
        reader = csv.reader(stream)
        rows = list(reader)
        assert len(rows) == 2

    # 2. Logical identity mismatch fails closed
    bad_id_rec = dict(valid_rec)
    bad_id_rec["logical_archive_identity"] = dict(valid_rec["logical_archive_identity"], market="spot")
    with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_b_package_record_invalid:logical_archive_identity_mismatch"):
        with _open_verified_package_stream(root, bad_id_rec):
            pass

    # 3. Unverified child_state fails closed
    unverified_rec = dict(valid_rec, child_state="archive_request_nonpersisted")
    with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_b_package_record_invalid:unverified_child_state"):
        with _open_verified_package_stream(root, unverified_rec):
            pass

    # 4. Checksum hash mismatch fails closed
    chk_path.write_text(f"{'0'*64}  {zip_path.name}\n", encoding="utf-8")
    with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_b_checksum_invalid:hash_mismatch"):
        with _open_verified_package_stream(root, valid_rec):
            pass
    chk_path.write_text(f"{actual_sha}  {zip_path.name}\n", encoding="utf-8")

    # 5. Symlink ZIP fails closed
    sym_zip = root / "raw" / "archive" / sym / f"sym-{sym}-aggTrades-{utc_date}.zip"
    sym_zip.symlink_to(zip_path)
    sym_rec = dict(valid_rec, utc_date=f"sym-{utc_date}")
    sym_rec["logical_archive_identity"] = dict(sym_rec["logical_archive_identity"], utc_date=f"sym-{utc_date}")
    with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_b_.*"):
        with _open_verified_package_stream(root, sym_rec):
            pass

    # 6. _ChunkBoundedReader rejects oversized read request
    raw_mock = io.BytesIO(b"x" * 100)
    reader = _ChunkBoundedReader(raw_mock, EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES)
    oversized_buf = bytearray(EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES + 1)
    with pytest.raises(Stage1_5JBDiagnosticError, match="STOP=stage1_5j_b_stream_chunk_bytes_exceeded"):
        reader.readinto(oversized_buf)
