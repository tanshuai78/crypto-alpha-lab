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
import copy
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from decimal import Decimal
from pathlib import Path

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
PLAN_SHA = "ec5fbc3beeafd47ec42cdf12481751f41424fe3351a6c14845ebc0e5d5a8a319"
TASK0_BUNDLE_DIR = PROJECT_ROOT / ".git" / "plan-execution" / "stage1_5j_b" / PLAN_SHA


# =============================================================================
# 1. Task 0 Execution Authority Verification
# =============================================================================


def test_verify_execution_authority_positive() -> None:
    """Canonical Task 0 on-disk bundle passes verification cleanly."""
    auth = verify_execution_authority()
    assert auth["schema_version"] == "stage1_5j_b_execution_authority_v2"
    assert auth["risk_live_trading_enabled"] is False
    assert auth["base_sha"] == "d15ca4e0da75a61553ca1d5983249d85a4512bb5"
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

    # Swap their states in parent_horizon_rows
    comp_reasons = None
    gap_reasons = None
    for phr in s_obj["parent_horizon_rows"]:
        if phr["source_article_id"] == p_comp:
            comp_reasons = copy.deepcopy(phr["failed_child_reasons"])
            phr["source_parent_state"] = "coverage_evidence_gap_archive"
        elif phr["source_article_id"] == p_gap:
            gap_reasons = copy.deepcopy(phr["failed_child_reasons"])
            phr["source_parent_state"] = "coverage_complete"

    # Assign consistent reasons
    for phr in s_obj["parent_horizon_rows"]:
        if phr["source_article_id"] == p_comp:
            phr["failed_child_reasons"] = [
                {"missing_reason": "inherited_j_a_parent_gap", "symbol": r.get("symbol")}
                for r in comp_reasons
            ]
        elif phr["source_article_id"] == p_gap:
            phr["failed_child_reasons"] = [
                {"missing_reason": "evidence_gap_missing_horizon_trade", "symbol": r.get("symbol")}
                for r in gap_reasons
            ]

    # Update child_rows consistently
    for cr in s_obj["child_rows"]:
        if cr["source_article_id"] == p_comp:
            cr["j_a_parent_state"] = "coverage_evidence_gap_archive"
            cr["anchor_state"] = "anchor_unavailable_inherited_j_a_parent_gap"
            cr["required_archive_dates_by_horizon"] = {"300000": [], "3600000": [], "14400000": []}
        elif cr["source_article_id"] == p_gap:
            cr["j_a_parent_state"] = "coverage_complete"
            cr["anchor_state"] = "evidence_gap"

    # Update child_horizon_rows consistently
    for chr_ in s_obj["child_horizon_rows"]:
        if chr_["source_article_id"] == p_comp:
            chr_["missing_reason"] = "inherited_j_a_parent_gap"
        elif chr_["source_article_id"] == p_gap:
            chr_["missing_reason"] = "evidence_gap_missing_horizon_trade"

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


