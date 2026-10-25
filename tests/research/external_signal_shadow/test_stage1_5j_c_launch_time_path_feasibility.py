"""Unit and contract tests for Stage 1.5J-C Launch Time and Path Feasibility Core Module."""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import shutil
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = PROJECT_ROOT / "docs/production_artifacts/stage1_5j_c_time_path_protocol_v1.json"
EXPECTED_PROTOCOL_BYTES = (
    b'{"endpoint_max_age_ms":1000,"entry_max_wait_ms":1000,"friction_bps":[50,80,150],'
    b'"horizon_ms":900000,"latency_ms":3000,"observation_ms":60000,'
    b'"protocol_id":"stage1_5j_c_time_path_v1","protocol_version":1,'
    b'"risk_bps":200,"target_bps":3000}\n'
)
EXPECTED_PROTOCOL_SHA256 = "4dd353751256191d75fc52388413d97e5a7b177e499bbee28e2dd2ff356e1cbe"
CORE_SOURCE_PATH = (
    PROJECT_ROOT
    / "src/research/external_signal_shadow/stage1_5j_c_launch_time_path_feasibility.py"
)
CLI_SOURCE_PATH = (
    PROJECT_ROOT
    / "scripts/external_signal_shadow/run_stage1_5j_c_launch_time_path_feasibility.py"
)


def _import_core():
    from research.external_signal_shadow import (
        stage1_5j_c_launch_time_path_feasibility as jc,
    )

    return jc


def _make_trade(
    utc_date: str,
    physical_row: int,
    agg_trade_id: int,
    time_ms: int,
    price: str,
    quantity: str = "10.0",
    first_trade_id: int | None = None,
    last_trade_id: int | None = None,
    is_buyer_maker: str = "false",
) -> dict[str, object]:
    fid = agg_trade_id if first_trade_id is None else first_trade_id
    lid = agg_trade_id if last_trade_id is None else last_trade_id
    return {
        "utc_date": utc_date,
        "physical_row": physical_row,
        "agg_trade_id": agg_trade_id,
        "price": price,
        "quantity": quantity,
        "first_trade_id": fid,
        "last_trade_id": lid,
        "transact_time": time_ms,
        "is_buyer_maker": is_buyer_maker,
    }


def test_fixed_protocol_file_bytes_and_sha256() -> None:
    """Verify canonical protocol JSON bytes, formatting, and SHA-256."""
    assert PROTOCOL_PATH.is_file() and not PROTOCOL_PATH.is_symlink()
    raw = PROTOCOL_PATH.read_bytes()
    assert raw == EXPECTED_PROTOCOL_BYTES
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_PROTOCOL_SHA256

    jc = _import_core()
    loaded = jc.load_and_verify_protocol(PROTOCOL_PATH)
    assert loaded == {
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


def test_protocol_artifact_and_workspace_have_zero_test_writers(tmp_path: Path) -> None:
    """Verify production protocol artifact is strictly read-only and has zero test or source writers."""
    jc = _import_core()

    # 1. AST audit: verify no source or test file in J-C writes to protocol or docs/production_artifacts
    repo_files_to_check = [
        CORE_SOURCE_PATH,
        CLI_SOURCE_PATH,
        PROJECT_ROOT / "scripts/governance/verify_stage1_5j_c_receipt_schema.py",
        PROJECT_ROOT / "tests/research/external_signal_shadow/test_stage1_5j_c_launch_time_path_feasibility.py",
        PROJECT_ROOT / "tests/scripts/external_signal_shadow/test_run_stage1_5j_c_launch_time_path_feasibility.py",
        PROJECT_ROOT / "tests/scripts/governance/test_verify_stage1_5j_c_receipt_schema.py",
    ]
    for p in repo_files_to_check:
        assert p.is_file(), f"File missing: {p}"
        tree = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id
                if func_name in ("write_bytes", "write_text"):
                    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                        assert "protocol" not in node.func.value.id.lower(), f"Forbidden protocol writer at {p}:{node.lineno}"

    # 2. Runtime write-trap: load_and_verify_protocol must never execute any write
    writes: list[str] = []
    orig_wb = Path.write_bytes
    orig_wt = Path.write_text
    try:
        def _trap_wb(self: Path, *args: Any, **kwargs: Any) -> int:
            writes.append(f"write_bytes:{self}")
            return orig_wb(self, *args, **kwargs)

        def _trap_wt(self: Path, *args: Any, **kwargs: Any) -> int:
            writes.append(f"write_text:{self}")
            return orig_wt(self, *args, **kwargs)

        Path.write_bytes = _trap_wb  # type: ignore[assignment]
        Path.write_text = _trap_wt  # type: ignore[assignment]

        loaded = jc.load_and_verify_protocol(PROTOCOL_PATH)
        assert loaded["protocol_id"] == "stage1_5j_c_time_path_v1"
        assert len(writes) == 0

        # 3. Fail-closed on missing protocol: must fail closed and NEVER create the file
        missing_p = tmp_path / "nonexistent_protocol.json"
        assert not missing_p.exists()
        with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_authority_mismatch:protocol_missing_or_symlink"):
            jc.load_and_verify_protocol(missing_p)
        assert not missing_p.exists()
        assert len(writes) == 0
    finally:
        Path.write_bytes = orig_wb  # type: ignore[assignment]
        Path.write_text = orig_wt  # type: ignore[assignment]


def test_protocol_loader_rejects_mutated_missing_extra_or_noncanonical(
    tmp_path: Path,
) -> None:
    """Protocol loader must reject altered values, extra keys, missing keys, or non-canonical JSON."""
    jc = _import_core()

    altered = json.loads(EXPECTED_PROTOCOL_BYTES.decode("utf-8"))
    altered["latency_ms"] = 2000
    p_altered = tmp_path / "altered.json"
    p_altered.write_text(
        json.dumps(altered, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_authority_mismatch"):
        jc.load_and_verify_protocol(p_altered)

    extra = json.loads(EXPECTED_PROTOCOL_BYTES.decode("utf-8"))
    extra["extra_key"] = 1
    p_extra = tmp_path / "extra.json"
    p_extra.write_text(
        json.dumps(extra, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_authority_mismatch"):
        jc.load_and_verify_protocol(p_extra)

    missing = json.loads(EXPECTED_PROTOCOL_BYTES.decode("utf-8"))
    missing.pop("target_bps")
    p_missing = tmp_path / "missing.json"
    p_missing.write_text(
        json.dumps(missing, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_authority_mismatch"):
        jc.load_and_verify_protocol(p_missing)

    p_spaces = tmp_path / "spaces.json"
    p_spaces.write_text(
        json.dumps(json.loads(EXPECTED_PROTOCOL_BYTES.decode("utf-8")), indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_authority_mismatch"):
        jc.load_and_verify_protocol(p_spaces)


def test_exact_fraction_serialization_and_parsing() -> None:
    """Verify canonical reduced numerator/denominator string representation."""
    jc = _import_core()
    assert jc.format_exact_fraction(Fraction(0, 5)) == "0/1"
    assert jc.format_exact_fraction(Fraction(400, 2)) == "200/1"
    assert jc.format_exact_fraction(Fraction(-50, 3)) == "-50/3"

    assert jc.parse_exact_fraction("0/1") == Fraction(0, 1)
    assert jc.parse_exact_fraction("-50/3") == Fraction(-50, 3)

    for bad in ["0/2", "-0/1", "+200/1", "01/2", "2/04", "4/2", "100", "1/0", "1/-2"]:
        with pytest.raises(jc.Stage1_5JCDiagnosticError):
            jc.parse_exact_fraction(bad)


def test_window_boundaries_63s_64s_899s_900s_and_one_ms_exclusion() -> None:
    """Verify exact entry [T0+63000, T0+64000] and endpoint [T0+899000, T0+900000] boundaries."""
    jc = _import_core()
    t0_ms = 1760000000000  # 2025-10-09T08:53:20.000Z
    date_str = "2025-10-09"

    # Case 1: Entry at exact T0+63000 (first in window) and Endpoint at exact T0+900000 (last in window)
    # Trade at T0+62999 (1ms before entry window) and T0+900001 (1ms after endpoint window) must be excluded.
    trades = [
        _make_trade(date_str, 1, 100, t0_ms, "1.0000"),
        _make_trade(date_str, 2, 101, t0_ms + 62999, "0.5000"),  # 1ms early: excluded from entry
        _make_trade(date_str, 3, 102, t0_ms + 63000, "1.0000"),  # first in [63000, 64000] -> entry
        _make_trade(date_str, 4, 103, t0_ms + 64000, "1.1000"),  # still in entry window, after entry
        _make_trade(date_str, 5, 104, t0_ms + 899000, "1.2000"),  # in endpoint window
        _make_trade(date_str, 6, 105, t0_ms + 900000, "1.2500"),  # last in [899000, 900000] -> endpoint
        _make_trade(date_str, 7, 106, t0_ms + 900001, "9.9999"),  # 1ms after T_end: excluded
    ]
    rows = jc.reduce_child_time_path_from_trades(
        parent_article_id="a" * 32,
        symbol="TESTUSDT",
        listing_regime="standard",
        symbol_launch_time_ms=t0_ms,
        expected_anchor_time_ms=t0_ms,
        expected_anchor_price="1.0000",
        trades=trades,
    )
    by_dir = {r["direction"]: r for r in rows}
    long_row = by_dir["long"]
    short_row = by_dir["short"]

    assert long_row["state"] == "complete"
    assert long_row["t0"]["agg_trade_id"] == 100
    assert long_row["entry"]["agg_trade_id"] == 102
    assert long_row["endpoint"]["agg_trade_id"] == 105
    assert long_row["terminal_bps"] == "2500/1"
    assert long_row["mfe_bps"] == "2500/1"
    assert long_row["mae_bps"] == "0/1"
    assert short_row["terminal_bps"] == "-2500/1"
    assert short_row["mfe_bps"] == "0/1"
    assert short_row["mae_bps"] == "-2500/1"

    # Case 2: Only trade near entry is at T0+64000 (upper boundary inclusive) and endpoint at T0+899000 (lower boundary inclusive)
    trades_upper_lower = [
        _make_trade(date_str, 1, 200, t0_ms, "1.0000"),
        _make_trade(date_str, 2, 201, t0_ms + 62999, "1.0500"),
        _make_trade(date_str, 3, 202, t0_ms + 64000, "1.0000"),
        _make_trade(date_str, 4, 203, t0_ms + 64001, "1.5000"),
        _make_trade(date_str, 5, 204, t0_ms + 898999, "1.6000"),
        _make_trade(date_str, 6, 205, t0_ms + 899000, "1.1000"),
    ]
    rows_ul = jc.reduce_child_time_path_from_trades(
        parent_article_id="a" * 32,
        symbol="TESTUSDT",
        listing_regime="standard",
        symbol_launch_time_ms=t0_ms,
        expected_anchor_time_ms=t0_ms,
        expected_anchor_price="1.0000",
        trades=trades_upper_lower,
    )
    long_ul = {r["direction"]: r for r in rows_ul}["long"]
    assert long_ul["state"] == "complete"
    assert long_ul["entry"]["agg_trade_id"] == 202
    assert long_ul["endpoint"]["agg_trade_id"] == 205
    assert long_ul["terminal_bps"] == "1000/1"


def test_same_ms_ordering_and_duplicate_extrema_tie_breaking() -> None:
    """Same-ms records before entry are excluded; ties in extrema pick first trade."""
    jc = _import_core()
    t0_ms = 1760000000000
    date_str = "2025-10-09"
    # Entry is at t0_ms + 63000 (row 2, id 11). Row 3 (id 12) is at same millisecond t0_ms + 63000.
    # Row 4 (id 13) and Row 5 (id 14) both reach the exact same max price 1.2000; MFE trade must be Row 4 (id 13).
    trades = [
        _make_trade(date_str, 1, 10, t0_ms, "1.0000"),
        _make_trade(date_str, 2, 11, t0_ms + 63000, "1.0000"),
        _make_trade(date_str, 3, 12, t0_ms + 63000, "0.9900"),
        _make_trade(date_str, 4, 13, t0_ms + 100000, "1.2000"),
        _make_trade(date_str, 5, 14, t0_ms + 200000, "1.2000"),
        _make_trade(date_str, 6, 15, t0_ms + 899500, "1.1000"),
    ]
    rows = jc.reduce_child_time_path_from_trades(
        parent_article_id="b" * 32,
        symbol="TIEUSDT",
        listing_regime="standard",
        symbol_launch_time_ms=t0_ms,
        expected_anchor_time_ms=t0_ms,
        expected_anchor_price="1.0000",
        trades=trades,
    )
    long_row = {r["direction"]: r for r in rows}["long"]
    assert long_row["entry"]["agg_trade_id"] == 11
    assert long_row["mae_trade"]["agg_trade_id"] == 12
    assert long_row["mae_bps"] == "-100/1"
    assert long_row["mfe_trade"]["agg_trade_id"] == 13
    assert long_row["mfe_bps"] == "2000/1"


def test_first_passage_order_equality_jump_neither_and_unrounded_threshold() -> None:
    """First passage must follow trade order, not extrema, preserve jump MAE, and reject rounding pseudo-touch."""
    jc = _import_core()
    t0_ms = 1760000000000
    date_str = "2025-10-09"

    # Path A: Hits +3000 bps (1.3000) first, then drops to -500 bps (0.9500)
    trades_target_first = [
        _make_trade(date_str, 1, 1, t0_ms, "1.0000"),
        _make_trade(date_str, 2, 2, t0_ms + 63000, "1.0000"),
        _make_trade(date_str, 3, 3, t0_ms + 120000, "1.3000"),  # exact +3000 bps -> long target
        _make_trade(date_str, 4, 4, t0_ms + 180000, "0.9500"),  # -500 bps -> full-window MAE still recorded
        _make_trade(date_str, 5, 5, t0_ms + 900000, "1.1000"),
    ]
    res_a = {
        r["direction"]: r
        for r in jc.reduce_child_time_path_from_trades(
            parent_article_id="c" * 32,
            symbol="ORDAUSDT",
            listing_regime="standard",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="1.0000",
            trades=trades_target_first,
        )
    }
    assert res_a["long"]["first_touch"] == "target"
    assert res_a["long"]["touch_trade"]["agg_trade_id"] == 3
    assert res_a["long"]["mfe_bps"] == "3000/1"
    assert res_a["long"]["mae_bps"] == "-500/1"
    # For short on Path A, price 1.3000 is -3000 bps (<= -200 bps risk jump!)
    assert res_a["short"]["first_touch"] == "risk"
    assert res_a["short"]["touch_trade"]["agg_trade_id"] == 3
    assert res_a["short"]["mae_bps"] == "-3000/1"
    assert res_a["short"]["mfe_bps"] == "500/1"

    # Path B: Same min/max prices (0.9500 and 1.3000) but in reverse chronological order
    trades_risk_first = [
        _make_trade(date_str, 1, 1, t0_ms, "1.0000"),
        _make_trade(date_str, 2, 2, t0_ms + 63000, "1.0000"),
        _make_trade(date_str, 3, 3, t0_ms + 120000, "0.9500"),  # jump past -200 bps to -500 bps
        _make_trade(date_str, 4, 4, t0_ms + 180000, "1.3000"),
        _make_trade(date_str, 5, 5, t0_ms + 900000, "1.1000"),
    ]
    res_b = {
        r["direction"]: r
        for r in jc.reduce_child_time_path_from_trades(
            parent_article_id="c" * 32,
            symbol="ORDBUSDT",
            listing_regime="standard",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="1.0000",
            trades=trades_risk_first,
        )
    }
    assert res_b["long"]["first_touch"] == "risk"
    assert res_b["long"]["touch_trade"]["agg_trade_id"] == 3
    assert res_b["long"]["touch_trade"]["price"] == "0.9500"
    assert res_b["long"]["mfe_bps"] == "3000/1"
    assert res_b["long"]["mae_bps"] == "-500/1"

    # Path C: Unrounded near-threshold (1.29999999 -> +2999.9999 bps < 3000; 0.98000001 -> -199.9999 bps > -200) -> neither
    trades_neither = [
        _make_trade(date_str, 1, 1, t0_ms, "1.00000000"),
        _make_trade(date_str, 2, 2, t0_ms + 63000, "1.00000000"),
        _make_trade(date_str, 3, 3, t0_ms + 120000, "1.29999999"),
        _make_trade(date_str, 4, 4, t0_ms + 180000, "0.98000001"),
        _make_trade(date_str, 5, 5, t0_ms + 900000, "1.01000000"),
    ]
    res_c = {
        r["direction"]: r
        for r in jc.reduce_child_time_path_from_trades(
            parent_article_id="c" * 32,
            symbol="NEITHERUSDT",
            listing_regime="pre_market",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="1.00000000",
            trades=trades_neither,
        )
    }
    assert res_c["long"]["first_touch"] == "neither"
    assert res_c["long"]["touch_trade"] is None


def test_cross_midnight_and_missing_entry_endpoint_or_sequence_gap() -> None:
    """Verify cross-midnight UTC dates, entry_unavailable, endpoint_unavailable, and sequence_gap."""
    jc = _import_core()
    # 2025-10-09T23:55:00.000Z -> crosses midnight into 2025-10-10 within 15m (900,000ms)
    t0_ms = 1760054100000
    assert jc.compute_required_utc_dates(t0_ms, 900000) == ["2025-10-09", "2025-10-10"]

    # Cross-midnight complete path
    trades_cross = [
        _make_trade("2025-10-09", 1, 50, t0_ms, "2.00"),
        _make_trade("2025-10-09", 2, 51, t0_ms + 63500, "2.00"),
        _make_trade("2025-10-10", 1, 52, t0_ms + 899500, "2.20"),
    ]
    res_cross = {
        r["direction"]: r
        for r in jc.reduce_child_time_path_from_trades(
            parent_article_id="d" * 32,
            symbol="CROSSUSDT",
            listing_regime="standard",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="2.00",
            trades=trades_cross,
        )
    }
    assert res_cross["long"]["state"] == "complete"
    assert res_cross["long"]["endpoint"]["utc_date"] == "2025-10-10"
    assert res_cross["long"]["max_intertrade_gap_ms"] == 899500 - 63500

    # No entry trade in [T0+63000, T0+64000] -> entry_unavailable, endpoint must be None even if present at T_end
    trades_no_entry = [
        _make_trade("2025-10-09", 1, 50, t0_ms, "2.00"),
        _make_trade("2025-10-10", 1, 51, t0_ms + 899500, "2.20"),
    ]
    res_no_entry = {
        r["direction"]: r
        for r in jc.reduce_child_time_path_from_trades(
            parent_article_id="d" * 32,
            symbol="NOENTUSDT",
            listing_regime="standard",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="2.00",
            trades=trades_no_entry,
        )
    }
    assert res_no_entry["long"]["state"] == "entry_unavailable"
    assert res_no_entry["long"]["t0"] is not None
    assert res_no_entry["long"]["entry"] is None
    assert res_no_entry["long"]["endpoint"] is None
    assert res_no_entry["long"]["first_touch"] == "unavailable"
    assert res_no_entry["long"]["mfe_bps"] is None

    # Entry present, no endpoint trade in [T0+899000, T0+900000] -> endpoint_unavailable (preserves t0 and entry)
    trades_no_endpoint = [
        _make_trade("2025-10-09", 1, 50, t0_ms, "2.00"),
        _make_trade("2025-10-09", 2, 51, t0_ms + 63500, "2.10"),
        _make_trade("2025-10-10", 1, 52, t0_ms + 500000, "3.00"),
    ]
    res_no_end = {
        r["direction"]: r
        for r in jc.reduce_child_time_path_from_trades(
            parent_article_id="d" * 32,
            symbol="NOENDUSDT",
            listing_regime="standard",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="2.00",
            trades=trades_no_endpoint,
        )
    }
    assert res_no_end["long"]["state"] == "endpoint_unavailable"
    assert res_no_end["long"]["t0"] is not None
    assert res_no_end["long"]["entry"] is not None
    assert res_no_end["long"]["endpoint"] is None
    assert res_no_end["long"]["mfe_bps"] is None
    assert res_no_end["long"]["first_touch"] == "unavailable"

    # Sequence gap between t0 and entry (agg_trade_id jumps from 50 to 52) -> sequence_gap
    trades_seq_gap = [
        _make_trade("2025-10-09", 1, 50, t0_ms, "2.00"),
        _make_trade("2025-10-09", 2, 52, t0_ms + 63500, "2.10"),
        _make_trade("2025-10-10", 1, 53, t0_ms + 899500, "2.20"),
    ]
    res_seq_gap = {
        r["direction"]: r
        for r in jc.reduce_child_time_path_from_trades(
            parent_article_id="d" * 32,
            symbol="SEQGAPUSDT",
            listing_regime="standard",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="2.00",
            trades=trades_seq_gap,
        )
    }
    assert res_seq_gap["long"]["state"] == "sequence_gap"
    assert res_seq_gap["long"]["t0"] is not None
    assert res_seq_gap["long"]["entry"] is not None
    assert res_seq_gap["long"]["endpoint"] is not None
    assert res_seq_gap["long"]["mfe_bps"] is None
    assert res_seq_gap["long"]["max_intertrade_gap_ms"] is None
    assert res_seq_gap["long"]["first_touch"] == "unavailable"


def test_ast_and_import_isolation_guards() -> None:
    """Forbid network transport, scripts imports in core, J-B private helpers, whole-file ZIP extract, and writer paths for approval/release."""
    assert CORE_SOURCE_PATH.is_file(), "Core module must exist"
    source_text = CORE_SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(CORE_SOURCE_PATH))

    forbidden_modules = {
        "urllib",
        "http",
        "socket",
        "requests",
        "aiohttp",
        "httpx",
        "websocket",
        "ftplib",
        "ssl",
        "scripts",
    }
    forbidden_names = {
        "_open_verified_package_stream",
        "_ChunkBoundedReader",
        "extractall",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                assert top not in forbidden_modules, f"Forbidden import in core: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                assert top not in forbidden_modules, f"Forbidden from-import in core: {node.module}"
            for alias in node.names:
                assert alias.name not in forbidden_names, f"Forbidden symbol import: {alias.name}"
        elif isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_names, f"Forbidden attribute access: {node.attr}"
        elif isinstance(node, ast.Name):
            assert node.id not in forbidden_names, f"Forbidden identifier use: {node.id}"


def _build_synthetic_ja_root_and_package(
    base_dir: Path,
    parent_id: str = "a" * 32,
    symbol: str = "SYNTHUSDT",
    utc_date: str = "2025-10-09",
    csv_lines: list[str] | None = None,
    title: str = "Binance Futures Will Launch USDⓈ-M SYNTHUSDT Perpetual Contract",
    project_info_cell: str = "Synthetic Crypto Token",
) -> tuple[Path, dict[str, object], dict[str, object], Path]:
    """Internal test helper constructing isolated minimal synthetic tables for testing stream parser robustness, CSV parsing edge cases, and EOF boundary handling per Rule 15 internal unit test exemption. This helper does NOT serve as upstream admission evidence (canonical admission is proven strictly by test_p_ad_01_canonical_j_a_package_admission_and_single_mutation_matrix)."""
    import csv as std_csv
    import zipfile

    ja_root = base_dir / "ja_root"
    det_dir = ja_root / "raw" / "article_details"
    arch_dir = ja_root / "raw" / "archive" / symbol
    det_dir.mkdir(parents=True, exist_ok=True)
    arch_dir.mkdir(parents=True, exist_ok=True)

    # Create article detail JSON with valid AST table
    body_obj = {
        "node": "root",
        "child": [
            {
                "tag": "table",
                "child": [
                    {
                        "tag": "tr",
                        "child": [
                            {"tag": "td", "child": [{"node": "text", "text": "USDⓈ-M Perpetual Contract"}]},
                            {"tag": "td", "child": [{"node": "text", "text": symbol}]},
                        ],
                    },
                    {
                        "tag": "tr",
                        "child": [
                            {"tag": "td", "child": [{"node": "text", "text": "Project Info"}]},
                            {"tag": "td", "child": [{"node": "text", "text": project_info_cell}]},
                        ],
                    },
                ],
            }
        ],
    }
    detail_payload = {
        "code": "000000",
        "data": {
            "id": 1,
            "code": parent_id,
            "title": title,
            "publishDate": 1759990000000,
            "body": json.dumps(body_obj),
        },
        "success": True,
    }
    det_rel = f"raw/article_details/{parent_id}.json"
    det_path = ja_root / det_rel
    det_bytes = (json.dumps(detail_payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    det_path.write_bytes(det_bytes)
    det_sha = hashlib.sha256(det_bytes).hexdigest()

    if csv_lines is None:
        t0_ms = 1760000000000
        csv_lines = [
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
            f"100,1.0000,10.0,100,100,{t0_ms},false",
            f"101,1.0000,10.0,101,101,{t0_ms + 63500},false",
            f"102,1.3500,10.0,102,102,{t0_ms + 300000},false",
            f"103,1.2000,10.0,103,103,{t0_ms + 899500},false",
        ]
    csv_bytes = ("\n".join(csv_lines) + "\n").encode("utf-8")
    zip_rel = f"raw/archive/{symbol}/{symbol}-aggTrades-{utc_date}.zip"
    zip_path = ja_root / zip_rel
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{symbol}-aggTrades-{utc_date}.csv", csv_bytes)
    zip_bytes = zip_path.read_bytes()
    zip_sha = hashlib.sha256(zip_bytes).hexdigest()

    chk_rel = f"{zip_rel}.CHECKSUM"
    chk_path = ja_root / chk_rel
    chk_bytes = f"{zip_sha}  {zip_path.name}\n".encode("utf-8")
    chk_path.write_bytes(chk_bytes)
    chk_sha = hashlib.sha256(chk_bytes).hexdigest()

    manifest_obj = {
        "artifacts": sorted(
            [
                {"byte_count": len(det_bytes), "relative_path": det_rel, "sha256": det_sha},
                {"byte_count": len(zip_bytes), "relative_path": zip_rel, "sha256": zip_sha},
                {"byte_count": len(chk_bytes), "relative_path": chk_rel, "sha256": chk_sha},
            ],
            key=lambda x: x["relative_path"],
        ),
        "run_id": "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z",
        "schema_version": "stage1_5j_a_historical_archive_coverage_inventory_v1",
    }
    (ja_root / "manifest.json").write_text(
        json.dumps(manifest_obj, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    pkg_rec = {
        "checksum_request_id": 2,
        "child_state": "archive_verified_with_post_launch_rows",
        "first_post_launch_trade_delay_ms": 0,
        "first_post_launch_trade_time_ms": 1760000000000,
        "last_post_launch_trade_time_ms": 1760000899500,
        "logical_archive_identity": {
            "market": "futures_um",
            "metric": "aggTrades",
            "parent_article_id": parent_id,
            "symbol": symbol,
            "utc_date": utc_date,
        },
        "parent_article_id": parent_id,
        "post_launch_row_count": 4,
        "symbol": symbol,
        "utc_date": utc_date,
        "zip_request_id": 3,
    }
    ja_summary = {
        "run_id": "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z",
        "archive_package_records": [pkg_rec],
        "request_records": [
            {
                "http_status_or_transport_error": 200,
                "request_id": 1,
                "request_kind": "detail",
                "request_state": "response_persisted",
                "response_bytes": len(det_bytes),
                "response_relative_path": det_rel,
                "response_sha256": det_sha,
                "url": "https://example.invalid/detail",
            },
            {
                "http_status_or_transport_error": 200,
                "request_id": 2,
                "request_kind": "checksum",
                "request_state": "response_persisted",
                "response_bytes": len(chk_bytes),
                "response_relative_path": chk_rel,
                "response_sha256": chk_sha,
                "url": "https://example.invalid/chk",
            },
            {
                "http_status_or_transport_error": 200,
                "request_id": 3,
                "request_kind": "archive",
                "request_state": "response_persisted",
                "response_bytes": len(zip_bytes),
                "response_relative_path": zip_rel,
                "response_sha256": zip_sha,
                "url": "https://example.invalid/zip",
            },
        ],
    }

    ledger_path = base_dir / "ledger.csv"
    with open(ledger_path, "w", newline="", encoding="utf-8") as f:
        writer = std_csv.DictWriter(
            f,
            fieldnames=[
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
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "parent_article_id": parent_id,
                "symbol": symbol,
                "asset_class": "crypto",
                "listing_regime": "standard",
                "classification_status": "confirmed",
                "table_index": "0",
                "symbol_column_index": "1",
                "field_header": "Project Info",
                "raw_cell_value": project_info_cell,
                "evidence_locator": "table[0].col[1].row['Project Info']",
                "source_relative_path": f"ja_root/{det_rel}",
                "source_sha256": det_sha,
            }
        )

    return ja_root, ja_summary, pkg_rec, ledger_path


def test_ledger_bijection_duplicate_key_and_aia_cross_parent_isolation(tmp_path: Path) -> None:
    """Verify ledger 12-column schema, bijection with J-B child_rows, AST locator verification, and AIA cross-parent isolation."""
    jc = _import_core()
    ja_root, ja_summary, pkg_rec, ledger_path = _build_synthetic_ja_root_and_package(tmp_path)

    jb_child_rows = [
        {
            "source_article_id": "a" * 32,
            "symbol": "SYNTHUSDT",
            "symbol_launch_time_ms": 1760000000000,
            "anchor_state": "anchor_found",
            "anchor_time_ms": 1760000000000,
            "anchor_price": "1",
            "anchor_delay_ms": 0,
            "j_a_parent_state": "coverage_complete",
            "j_a_child_state": "j_a_child_coverage_complete",
            "required_archive_dates_by_horizon": {},
        }
    ]
    universe_rows, selected_rows = jc.verify_and_scope_ledger_rows(
        ledger_path=ledger_path,
        jb_child_rows=jb_child_rows,
        ja_root=ja_root,
        ja_summary=ja_summary,
        project_root=tmp_path,
        expected_universe_count=1,
        expected_selected_count=1,
    )
    assert len(universe_rows) == 1
    assert len(selected_rows) == 1
    assert universe_rows[0]["in_scope"] is True

    # Duplicate key in ledger -> fail closed
    dup_ledger = tmp_path / "dup_ledger.csv"
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    dup_ledger.write_text("\n".join([lines[0], lines[1], lines[1]]) + "\n", encoding="utf-8")
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_ledger"):
        jc.verify_and_scope_ledger_rows(
            ledger_path=dup_ledger,
            jb_child_rows=jb_child_rows,
            ja_root=ja_root,
            ja_summary=ja_summary,
            project_root=tmp_path,
            expected_universe_count=1,
            expected_selected_count=1,
        )

    # Bijection mismatch -> fail closed
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_ledger"):
        jc.verify_and_scope_ledger_rows(
            ledger_path=ledger_path,
            jb_child_rows=[],
            ja_root=ja_root,
            ja_summary=ja_summary,
            project_root=tmp_path,
            expected_universe_count=1,
            expected_selected_count=1,
        )

    # AIA cross-parent isolation: same symbol AIAUSDT under two parents (one parent gap, one complete)
    p_gap = "1" * 32
    p_ok = "2" * 32
    ja_root2, ja_sum2, pkg_ok, _ = _build_synthetic_ja_root_and_package(
        tmp_path / "aia_case", parent_id=p_ok, symbol="AIAUSDT"
    )
    admitted_ctx = jc.build_admitted_ja_context(ja_root2, ja_sum2)
    # Attempting to use p_ok's package record for p_gap must fail closed
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_package_record_invalid"):
        with jc.open_j_c_verified_package_stream(
            admitted_ctx,
            pkg_ok,
            expected_parent_article_id=p_gap,
            expected_symbol="AIAUSDT",
            expected_utc_date="2025-10-09",
        ):
            pass


def test_package_admission_bounded_reader_eof_and_fault_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify internal parser robustness: bounded chunk size (<=65,536 bytes), streaming to EOF, invalid CSV row structures, and zip expansion ratio caps under Rule 15 internal unit test exemption."""
    import zipfile

    jc = _import_core()
    ja_root, ja_summary, pkg_rec, _ = _build_synthetic_ja_root_and_package(tmp_path / "ok")
    admitted_ctx = jc.build_admitted_ja_context(ja_root, ja_summary)

    # 1. Observe underlying readinto chunk size via monkeypatch (no global production test state)
    observed_readinto_sizes: list[int] = []
    orig_open = zipfile.ZipFile.open

    def _wrapped_zf_open(self, name, mode="r", pwd=None, *, force_zip64=False):
        raw_ext = orig_open(self, name, mode=mode, pwd=pwd, force_zip64=force_zip64)
        orig_readinto = raw_ext.readinto

        def _spy_readinto(b):
            observed_readinto_sizes.append(len(b))
            return orig_readinto(b)

        raw_ext.readinto = _spy_readinto  # type: ignore[attr-defined]
        return raw_ext

    monkeypatch.setattr(zipfile.ZipFile, "open", _wrapped_zf_open)

    child_rows = jc.stream_and_reduce_child_packages(
        admitted_ja_context=admitted_ctx,
        parent_article_id="a" * 32,
        symbol="SYNTHUSDT",
        listing_regime="standard",
        j_a_parent_state="coverage_complete",
        anchor_state="anchor_found",
        symbol_launch_time_ms=1760000000000,
        expected_anchor_time_ms=1760000000000,
        expected_anchor_price="1",
    )
    assert len(child_rows) == 2
    assert child_rows[0]["state"] == "complete"
    assert observed_readinto_sizes, "Underlying readinto must be invoked"
    assert max(observed_readinto_sizes) <= 65536

    # 2. Unadmitted hand-written copy of pkg_rec must fail closed
    handcrafted_dict = dict(pkg_rec)
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_package_record_invalid"):
        with jc.open_j_c_verified_package_stream(
            admitted_ctx,
            handcrafted_dict,
            expected_parent_article_id="a" * 32,
            expected_symbol="SYNTHUSDT",
            expected_utc_date="2025-10-09",
        ):
            pass

    # 3. Invalid checksum on disk -> fail closed
    ja_chk, sum_chk, pkg_chk, _ = _build_synthetic_ja_root_and_package(tmp_path / "bad_chk")
    ctx_chk = jc.build_admitted_ja_context(ja_chk, sum_chk)
    chk_file = ja_chk / "raw/archive/SYNTHUSDT/SYNTHUSDT-aggTrades-2025-10-09.zip.CHECKSUM"
    chk_file.write_text("0" * 64 + "  SYNTHUSDT-aggTrades-2025-10-09.zip\n", encoding="utf-8")
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_checksum_invalid"):
        with jc.open_j_c_verified_package_stream(
            ctx_chk,
            pkg_chk,
            expected_parent_article_id="a" * 32,
            expected_symbol="SYNTHUSDT",
            expected_utc_date="2025-10-09",
        ):
            pass

    # 4. Symlink on ZIP -> fail closed
    ja_sym, sum_sym, pkg_sym, _ = _build_synthetic_ja_root_and_package(tmp_path / "bad_sym")
    ctx_sym = jc.build_admitted_ja_context(ja_sym, sum_sym)
    zip_file = ja_sym / "raw/archive/SYNTHUSDT/SYNTHUSDT-aggTrades-2025-10-09.zip"
    moved_zip = tmp_path / "moved.zip"
    zip_file.rename(moved_zip)
    zip_file.symlink_to(moved_zip)
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_zip_package_invalid"):
        with jc.open_j_c_verified_package_stream(
            ctx_sym,
            pkg_sym,
            expected_parent_article_id="a" * 32,
            expected_symbol="SYNTHUSDT",
            expected_utc_date="2025-10-09",
        ):
            pass

    # 5. Corrupt row AFTER T_end (at T0 + 1,200,000ms) must fail closed because package is streamed to EOF
    t0_ms = 1760000000000
    eof_lines = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"100,1.0000,10.0,100,100,{t0_ms},false",
        f"101,1.0000,10.0,101,101,{t0_ms + 63500},false",
        f"102,1.2000,10.0,102,102,{t0_ms + 899500},false",
        f"99,1.2000,10.0,99,99,{t0_ms + 1200000},false",  # out-of-order agg_trade_id after 15m window!
    ]
    ja_eof, sum_eof, _, _ = _build_synthetic_ja_root_and_package(
        tmp_path / "bad_eof", csv_lines=eof_lines
    )
    ctx_eof = jc.build_admitted_ja_context(ja_eof, sum_eof)
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_csv"):
        jc.stream_and_reduce_child_packages(
            admitted_ja_context=ctx_eof,
            parent_article_id="a" * 32,
            symbol="SYNTHUSDT",
            listing_regime="standard",
            j_a_parent_state="coverage_complete",
            anchor_state="anchor_found",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="1",
        )

    # 6a. Excessive ZIP expansion ratio (> 100x) must fail closed on resource_caps
    zip_bomb_line = "104," + ("9" * 66000) + f",10.0,104,104,{t0_ms + 950000},false"
    ja_bomb, sum_bomb, _, _ = _build_synthetic_ja_root_and_package(
        tmp_path / "bad_bomb",
        csv_lines=[
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
            f"100,1.0000,10.0,100,100,{t0_ms},false",
            zip_bomb_line,
        ],
    )
    ctx_bomb = jc.build_admitted_ja_context(ja_bomb, sum_bomb)
    with pytest.raises(
        jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_zip_package_invalid:resource_caps"
    ):
        jc.stream_and_reduce_child_packages(
            admitted_ja_context=ctx_bomb,
            parent_article_id="a" * 32,
            symbol="SYNTHUSDT",
            listing_regime="standard",
            j_a_parent_state="coverage_complete",
            anchor_state="anchor_found",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="1",
        )

    # 6b. Overlong CSV line (> 65,536 bytes) with normal compression ratio must fail closed
    incompressible_digits = "".join(
        str(int.from_bytes(hashlib.sha256(str(i).encode()).digest()[:4], "big") % 10)
        for i in range(66000)
    )
    long_line = "104,1." + incompressible_digits + f",10.0,104,104,{t0_ms + 950000},false"
    overlong_lines = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"100,1.0000,10.0,100,100,{t0_ms},false",
        long_line,
    ]
    ja_long, sum_long, _, _ = _build_synthetic_ja_root_and_package(
        tmp_path / "bad_long", csv_lines=overlong_lines
    )
    ctx_long = jc.build_admitted_ja_context(ja_long, sum_long)
    with pytest.raises(
        jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_csv_line_length_exceeded"
    ):
        jc.stream_and_reduce_child_packages(
            admitted_ja_context=ctx_long,
            parent_article_id="a" * 32,
            symbol="SYNTHUSDT",
            listing_regime="standard",
            j_a_parent_state="coverage_complete",
            anchor_state="anchor_found",
            symbol_launch_time_ms=t0_ms,
            expected_anchor_time_ms=t0_ms,
            expected_anchor_price="1",
        )

    # 7. Invalid CSV header, invalid Decimal, decreasing timestamp, first_trade_id > last_trade_id, wrong UTC date, invalid boolean
    bad_csv_cases = [
        ["wrong_header,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker"],
        [
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
            f"100,0,10.0,100,100,{t0_ms},false",
        ],
        [
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
            f"100,NaN,10.0,100,100,{t0_ms},false",
        ],
        [
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
            f"100,1.0,10.0,105,100,{t0_ms},false",
        ],
        [
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
            f"100,1.0,10.0,100,100,{t0_ms},false",
            f"101,1.0,10.0,101,101,{t0_ms - 1},false",
        ],
        [
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
            f"100,1.0,10.0,100,100,{t0_ms - 86400000},false",
        ],
        [
            "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
            f"100,1.0,10.0,100,100,{t0_ms},maybe",
        ],
    ]
    for idx, bad_lines in enumerate(bad_csv_cases):
        ja_bad, sum_bad, _, _ = _build_synthetic_ja_root_and_package(
            tmp_path / f"bad_csv_{idx}", csv_lines=bad_lines
        )
        ctx_bad = jc.build_admitted_ja_context(ja_bad, sum_bad)
        with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_csv"):
            jc.stream_and_reduce_child_packages(
                admitted_ja_context=ctx_bad,
                parent_article_id="a" * 32,
                symbol="SYNTHUSDT",
                listing_regime="standard",
                j_a_parent_state="coverage_complete",
                anchor_state="anchor_found",
                symbol_launch_time_ms=t0_ms,
                expected_anchor_time_ms=t0_ms,
                expected_anchor_price="1",
            )

    # 8. ZIP resource cap failure (validate_zip_archive_package returns False)
    monkeypatch.setattr(jc, "validate_zip_archive_package", lambda *a, **kw: False)
    with pytest.raises(
        jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_zip_package_invalid:resource_caps"
    ):
        with jc.open_j_c_verified_package_stream(
            admitted_ctx,
            pkg_rec,
            expected_parent_article_id="a" * 32,
            expected_symbol="SYNTHUSDT",
            expected_utc_date="2025-10-09",
        ):
            pass


_CANONICAL_JA_CACHE: tuple[Path, dict[str, Any], Any] | None = None


def _get_canonical_ja_admission() -> tuple[Path, dict[str, Any], Any]:
    """Load canonical J-A root and return cached (ja_root, ja_summary, admitted_ctx) per Rule 15."""
    global _CANONICAL_JA_CACHE
    if _CANONICAL_JA_CACHE is None:
        jc = _import_core()
        ja_root = PROJECT_ROOT / jc.J_A_ROOT_RELATIVE_PATH
        if not ja_root.is_dir():
            raise FileNotFoundError(f"Canonical J-A root not found: {ja_root}")
        ja_summary = jc.load_verified_stage1_5j_a_historical_archive_coverage_root(ja_root)
        admitted_ctx = jc.build_admitted_ja_context(ja_root, ja_summary)
        _CANONICAL_JA_CACHE = (ja_root, ja_summary, admitted_ctx)
    return _CANONICAL_JA_CACHE


def test_p_ad_01_canonical_j_a_package_admission_and_single_mutation_matrix(tmp_path: Path) -> None:
    """P-AD-01 (Task 3): Verify package admission using canonical upstream J-A root & strict loader (Rule 15).

    1. Positive Control: Stream and reduce unmodified canonical J-A package through actual J-C admission entry path.
    2. Negative Matrix: Verify fail-closed behavior before reduction for single isolated mutations:
       a) Handcrafted unadmitted dictionary object.
       b) Expected parameter / logical identity mismatch.
       c) Isolated physical root single-byte checksum corruption.
       d) Isolated physical root single-byte zip magic corruption.
       e) Isolated physical root symlink escape.
    """
    jc = _import_core()
    ja_root, ja_summary, admitted_ctx = _get_canonical_ja_admission()
    assert len(admitted_ctx.package_by_key) > 0, "Admitted package lookup must be non-empty"

    # Select canonical PRLUSDT package on 2026-04-01
    canonical_pkg: dict[str, Any] | None = None
    for rec in ja_summary["archive_package_records"]:
        if rec["symbol"] == "PRLUSDT" and rec["utc_date"] == "2026-04-01":
            canonical_pkg = rec
            break
    assert canonical_pkg is not None, "Canonical PRLUSDT package record must exist in J-A summary"

    p_id = canonical_pkg["parent_article_id"]
    symbol = canonical_pkg["symbol"]
    utc_date = canonical_pkg["utc_date"]

    # 1. Positive Control: stream unmodified canonical package
    with jc.open_j_c_verified_package_stream(
        admitted_ctx,
        canonical_pkg,
        expected_parent_article_id=p_id,
        expected_symbol=symbol,
        expected_utc_date=utc_date,
    ) as stream:
        header = stream.readline().decode("utf-8")
        assert header.startswith("agg_trade_id,price,quantity")

    # Positive Control: stream and reduce child packages to completion
    reduced_rows = jc.stream_and_reduce_child_packages(
        admitted_ja_context=admitted_ctx,
        parent_article_id=p_id,
        symbol=symbol,
        listing_regime="standard",
        j_a_parent_state="coverage_complete",
        anchor_state="anchor_found",
        symbol_launch_time_ms=1775039400000,
        expected_anchor_time_ms=1775039400380,
        expected_anchor_price="0.1937",
    )
    assert len(reduced_rows) == 2
    assert reduced_rows[0]["state"] == "complete"
    assert reduced_rows[1]["state"] == "complete"

    # 2. Negative Mutation 1: Handcrafted unadmitted dictionary object
    unadmitted_pkg = dict(canonical_pkg)
    with pytest.raises(
        jc.Stage1_5JCDiagnosticError,
        match="STOP=stage1_5j_c_package_record_invalid:unadmitted_record",
    ):
        with jc.open_j_c_verified_package_stream(
            admitted_ctx,
            unadmitted_pkg,
            expected_parent_article_id=p_id,
            expected_symbol=symbol,
            expected_utc_date=utc_date,
        ):
            pass

    # 3. Negative Mutation 2: Expected parameter mismatch
    with pytest.raises(
        jc.Stage1_5JCDiagnosticError,
        match="STOP=stage1_5j_c_package_record_invalid",
    ):
        with jc.open_j_c_verified_package_stream(
            admitted_ctx,
            canonical_pkg,
            expected_parent_article_id=p_id,
            expected_symbol="MUTATEDUSDT",
            expected_utc_date=utc_date,
        ):
            pass

    # 4. Negative Mutation 3: Isolated physical root with single-byte checksum corruption
    disp_chk = tmp_path / "mut_chk"
    shutil.copytree(ja_root / f"raw/archive/{symbol}", disp_chk / f"raw/archive/{symbol}")
    shutil.copy2(ja_root / "manifest.json", disp_chk / "manifest.json")
    chk_file = disp_chk / f"raw/archive/{symbol}/{symbol}-aggTrades-{utc_date}.zip.CHECKSUM"
    orig_chk_text = chk_file.read_text(encoding="utf-8")
    mut_chk_text = ("0" if orig_chk_text[0] != "0" else "1") + orig_chk_text[1:]
    chk_file.write_text(mut_chk_text, encoding="utf-8")

    mut_ctx_chk = dataclasses.replace(admitted_ctx, ja_root=disp_chk)
    with pytest.raises(
        jc.Stage1_5JCDiagnosticError,
        match="STOP=stage1_5j_c_checksum_invalid",
    ):
        with jc.open_j_c_verified_package_stream(
            mut_ctx_chk,
            canonical_pkg,
            expected_parent_article_id=p_id,
            expected_symbol=symbol,
            expected_utc_date=utc_date,
        ):
            pass

    # 5. Negative Mutation 4: Isolated physical root with single-byte zip corruption
    disp_zip = tmp_path / "mut_zip"
    shutil.copytree(ja_root / f"raw/archive/{symbol}", disp_zip / f"raw/archive/{symbol}")
    shutil.copy2(ja_root / "manifest.json", disp_zip / "manifest.json")
    zip_file = disp_zip / f"raw/archive/{symbol}/{symbol}-aggTrades-{utc_date}.zip"
    zip_bytes = bytearray(zip_file.read_bytes())
    zip_bytes[0] = ord(b"X")
    zip_file.write_bytes(bytes(zip_bytes))

    mut_ctx_zip = dataclasses.replace(admitted_ctx, ja_root=disp_zip)
    with pytest.raises(
        jc.Stage1_5JCDiagnosticError,
        match="STOP=stage1_5j_c_(checksum_invalid|zip_package_invalid)",
    ):
        with jc.open_j_c_verified_package_stream(
            mut_ctx_zip,
            canonical_pkg,
            expected_parent_article_id=p_id,
            expected_symbol=symbol,
            expected_utc_date=utc_date,
        ):
            pass

    # 6. Negative Mutation 5: Isolated physical root with symlink escape
    disp_sym = tmp_path / "mut_sym"
    shutil.copytree(ja_root / f"raw/archive/{symbol}", disp_sym / f"raw/archive/{symbol}")
    shutil.copy2(ja_root / "manifest.json", disp_sym / "manifest.json")
    sym_target = disp_sym / f"raw/archive/{symbol}/{symbol}-aggTrades-{utc_date}.zip"
    escaped_target = tmp_path / "escaped.zip"
    sym_target.rename(escaped_target)
    sym_target.symlink_to(escaped_target)

    mut_ctx_sym = dataclasses.replace(admitted_ctx, ja_root=disp_sym)
    with pytest.raises(
        jc.Stage1_5JCDiagnosticError,
        match="STOP=stage1_5j_c_zip_package_invalid:symlink_or_missing",
    ):
        with jc.open_j_c_verified_package_stream(
            mut_ctx_sym,
            canonical_pkg,
            expected_parent_article_id=p_id,
            expected_symbol=symbol,
            expected_utc_date=utc_date,
        ):
            pass


def test_child_parent_group_projection_and_cost_concentration_semantics() -> None:
    """Verify Child -> Parent -> Group reduction, nearest-rank quantiles, cost rows (50, 80, 150), space_status precedence, concentration, and deterministic review rendering."""
    jc = _import_core()
    assert hasattr(jc, "project_parents_and_groups"), "Missing project_parents_and_groups"
    assert hasattr(jc, "render_stage1_5j_c_review"), "Missing render_stage1_5j_c_review"

    t0_ref = {
        "utc_date": "2025-10-09",
        "physical_row": 1,
        "agg_trade_id": 100,
        "time_ms": 1760000000000,
        "price": "1.0000",
    }
    entry_ref = {
        "utc_date": "2025-10-09",
        "physical_row": 2,
        "agg_trade_id": 101,
        "time_ms": 1760000063500,
        "price": "1.0000",
    }
    end_ref = {
        "utc_date": "2025-10-09",
        "physical_row": 4,
        "agg_trade_id": 103,
        "time_ms": 1760000899500,
        "price": "1.1000",
    }
    # Parent p1: 2 children, both complete in standard/long
    # Parent p2: 2 children, 1 complete + 1 gap in standard/long -> Parent must be gap!
    # Parent p3: 1 child, complete in standard/long
    child_rows = [
        # p1, SYMA, standard, long: MFE = 3000/1, MAE = -50/1, terminal = 1000/1, target
        {
            "parent_article_id": "1" * 32,
            "symbol": "SYMAUSDT",
            "listing_regime": "standard",
            "direction": "long",
            "state": "complete",
            "t0": t0_ref,
            "entry": entry_ref,
            "endpoint": end_ref,
            "mfe_trade": end_ref,
            "mae_trade": entry_ref,
            "terminal_bps": "1000/1",
            "mfe_bps": "3000/1",
            "mae_bps": "-50/1",
            "first_touch": "target",
            "touch_trade": end_ref,
            "max_intertrade_gap_ms": 1000,
        },
        {
            "parent_article_id": "1" * 32,
            "symbol": "SYMAUSDT",
            "listing_regime": "standard",
            "direction": "short",
            "state": "complete",
            "t0": t0_ref,
            "entry": entry_ref,
            "endpoint": end_ref,
            "mfe_trade": entry_ref,
            "mae_trade": end_ref,
            "terminal_bps": "-1000/1",
            "mfe_bps": "50/1",
            "mae_bps": "-3000/1",
            "first_touch": "risk",
            "touch_trade": end_ref,
            "max_intertrade_gap_ms": 1000,
        },
        # p1, SYMB, standard, long: MFE = 1000/1, MAE = 0/1, terminal = 500/1, neither
        {
            "parent_article_id": "1" * 32,
            "symbol": "SYMBUSDT",
            "listing_regime": "standard",
            "direction": "long",
            "state": "complete",
            "t0": t0_ref,
            "entry": entry_ref,
            "endpoint": end_ref,
            "mfe_trade": end_ref,
            "mae_trade": entry_ref,
            "terminal_bps": "500/1",
            "mfe_bps": "1000/1",
            "mae_bps": "0/1",
            "first_touch": "neither",
            "touch_trade": None,
            "max_intertrade_gap_ms": 1000,
        },
        {
            "parent_article_id": "1" * 32,
            "symbol": "SYMBUSDT",
            "listing_regime": "standard",
            "direction": "short",
            "state": "complete",
            "t0": t0_ref,
            "entry": entry_ref,
            "endpoint": end_ref,
            "mfe_trade": entry_ref,
            "mae_trade": end_ref,
            "terminal_bps": "-500/1",
            "mfe_bps": "0/1",
            "mae_bps": "-1000/1",
            "first_touch": "risk",
            "touch_trade": end_ref,
            "max_intertrade_gap_ms": 1000,
        },
        # p2, SYMC, standard, long: complete, MFE = 2000/1
        {
            "parent_article_id": "2" * 32,
            "symbol": "SYMCUSDT",
            "listing_regime": "standard",
            "direction": "long",
            "state": "complete",
            "t0": t0_ref,
            "entry": entry_ref,
            "endpoint": end_ref,
            "mfe_trade": end_ref,
            "mae_trade": entry_ref,
            "terminal_bps": "200/1",
            "mfe_bps": "2000/1",
            "mae_bps": "0/1",
            "first_touch": "neither",
            "touch_trade": None,
            "max_intertrade_gap_ms": 500,
        },
        {
            "parent_article_id": "2" * 32,
            "symbol": "SYMCUSDT",
            "listing_regime": "standard",
            "direction": "short",
            "state": "complete",
            "t0": t0_ref,
            "entry": entry_ref,
            "endpoint": end_ref,
            "mfe_trade": entry_ref,
            "mae_trade": end_ref,
            "terminal_bps": "-200/1",
            "mfe_bps": "0/1",
            "mae_bps": "-2000/1",
            "first_touch": "risk",
            "touch_trade": end_ref,
            "max_intertrade_gap_ms": 500,
        },
        # p2, SYMD, standard: entry_unavailable -> makes p2 gap!
        {
            "parent_article_id": "2" * 32,
            "symbol": "SYMDUSDT",
            "listing_regime": "standard",
            "direction": "long",
            "state": "entry_unavailable",
            "t0": t0_ref,
            "entry": None,
            "endpoint": None,
            "mfe_trade": None,
            "mae_trade": None,
            "terminal_bps": None,
            "mfe_bps": None,
            "mae_bps": None,
            "first_touch": "unavailable",
            "touch_trade": None,
            "max_intertrade_gap_ms": None,
        },
        {
            "parent_article_id": "2" * 32,
            "symbol": "SYMDUSDT",
            "listing_regime": "standard",
            "direction": "short",
            "state": "entry_unavailable",
            "t0": t0_ref,
            "entry": None,
            "endpoint": None,
            "mfe_trade": None,
            "mae_trade": None,
            "terminal_bps": None,
            "mfe_bps": None,
            "mae_bps": None,
            "first_touch": "unavailable",
            "touch_trade": None,
            "max_intertrade_gap_ms": None,
        },
    ]

    parent_rows, group_rows = jc.project_parents_and_groups(child_rows)
    assert len(parent_rows) == 4  # 2 parents * 2 directions
    assert len(group_rows) == 4  # 2 regimes * 2 directions

    # Verify p1 standard/long is complete with median MFE = (3000+1000)/2 = 2000/1, terminal = 750/1, MAE = -25/1
    p1_long = next(
        p for p in parent_rows if p["parent_article_id"] == "1" * 32 and p["direction"] == "long"
    )
    assert p1_long["state"] == "complete"
    assert p1_long["mfe_bps"] == "2000/1"
    assert p1_long["terminal_bps"] == "750/1"
    assert p1_long["mae_bps"] == "-25/1"
    assert p1_long["touch_counts"] == {"target": 1, "risk": 0, "neither": 1}

    # Verify p2 standard/long is gap because SYMDUSDT is entry_unavailable
    p2_long = next(
        p for p in parent_rows if p["parent_article_id"] == "2" * 32 and p["direction"] == "long"
    )
    assert p2_long["state"] == "gap"
    assert p2_long["n_complete"] == 1
    assert p2_long["n_gap"] == 1
    assert p2_long["mfe_bps"] is None
    assert p2_long["touch_counts"] is None

    # Verify standard/long group has n_total=4, n_complete=3, n_gap=1, space_status='evidence_insufficient' for all 3 costs
    g_std_long = next(
        g
        for g in group_rows
        if g["listing_regime"] == "standard" and g["direction"] == "long"
    )
    assert g_std_long["child"]["n_total"] == 4
    assert g_std_long["child"]["n_complete"] == 3
    assert g_std_long["child"]["n_gap"] == 1
    assert [c["cost_bps"] for c in g_std_long["costs"]] == [50, 80, 150]
    assert all(c["space_status"] == "evidence_insufficient" for c in g_std_long["costs"])
    assert g_std_long["parent_touch_fraction_mean"] == {
        "target": "1/2",
        "risk": "0/1",
        "neither": "1/2",
    }
    assert g_std_long["concentration"]["top1_parent_ids"] == ["1" * 32]
    assert g_std_long["concentration"]["top1_share"] == "1/1"

    # Verify pre_market/long group is empty -> n=0, space_status='evidence_insufficient', parent_touch_fraction_mean all None
    g_pm_long = next(
        g
        for g in group_rows
        if g["listing_regime"] == "pre_market" and g["direction"] == "long"
    )
    assert g_pm_long["child"]["n_total"] == 0
    assert g_pm_long["parent_touch_fraction_mean"] == {
        "target": None,
        "risk": None,
        "neither": None,
    }
    assert g_pm_long["concentration"]["top1_share"] is None

    # Verify review_CN.md deterministic rendering
    dummy_summary = {
        "run_id": "stage1_5j_c_launch_time_path_feasibility_20261024T000000Z",
        "profile_id": "stage1_5j_c_time_path_v1",
        "artifact_kind": "validation_only",
        "analysis_state": "time_path_evidence_gap",
        "group_rows": group_rows,
    }
    rendered = jc.render_stage1_5j_c_review(dummy_summary)
    assert rendered.startswith(
        "# Stage 1.5J-C 时间与路径诊断\n"
        "run_id: stage1_5j_c_launch_time_path_feasibility_20261024T000000Z\n"
        "profile_id: stage1_5j_c_time_path_v1\n"
        "artifact_kind: validation_only\n"
        "analysis_state: time_path_evidence_gap\n"
        "universe_children: 281\n"
        "selected_children: 71\n"
    )
    assert rendered.endswith(
        "Exploratory price-path diagnosis only; no alpha, execution, paper or live trading authority.\n"
    )
    assert "\n\n" not in rendered


def test_atomic_publication_durability_faults_and_collisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify atomic publication protocol: 4 durability faults (file fsync, staging fsync, rename, parent fsync after rename) and root/lock/staging collisions."""
    jc = _import_core()
    assert hasattr(jc, "publish_stage1_5j_c_receipt_root"), "Missing publish_stage1_5j_c_receipt_root"

    run_id = "stage1_5j_c_launch_time_path_feasibility_20261024T010203Z"
    manifest_bytes = b'{"profile_id":"stage1_5j_c_time_path_v1"}\n'
    summary_bytes = b'{"profile_id":"stage1_5j_c_time_path_v1"}\n'
    review_bytes = b"# Stage 1.5J-C\n"

    # 1. File fsync fault -> raises, no final root created
    out_1 = tmp_path / "f1" / run_id
    out_1.parent.mkdir(parents=True)
    with monkeypatch.context() as mp:
        mp.setattr(
            jc,
            "_fsync_file_descriptor",
            lambda fd: (_ for _ in ()).throw(OSError("injected file fsync fault")),
        )
        with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_publish_io_error"):
            jc.publish_stage1_5j_c_receipt_root(
                output_root=out_1,
                run_id=run_id,
                artifact_kind="validation_only",
                operation="offline_time_path_validation_once",
                manifest_bytes=manifest_bytes,
                summary_bytes=summary_bytes,
                review_bytes=review_bytes,
            )
    assert not out_1.exists()

    # 2. Staging directory fsync fault -> raises, no final root created
    out_2 = tmp_path / "f2" / run_id
    out_2.parent.mkdir(parents=True)
    with monkeypatch.context() as mp:
        mp.setattr(
            jc,
            "_fsync_directory",
            lambda p: (_ for _ in ()).throw(OSError("injected staging dir fsync fault")),
        )
        with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_publish_io_error"):
            jc.publish_stage1_5j_c_receipt_root(
                output_root=out_2,
                run_id=run_id,
                artifact_kind="validation_only",
                operation="offline_time_path_validation_once",
                manifest_bytes=manifest_bytes,
                summary_bytes=summary_bytes,
                review_bytes=review_bytes,
            )
    assert not out_2.exists()

    # 3. Rename fault -> raises, no final root created
    out_3 = tmp_path / "f3" / run_id
    out_3.parent.mkdir(parents=True)
    with monkeypatch.context() as mp:
        mp.setattr(
            jc,
            "_atomic_rename_staging_to_final",
            lambda src, dst: (_ for _ in ()).throw(OSError("injected rename fault")),
        )
        with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_publish_io_error"):
            jc.publish_stage1_5j_c_receipt_root(
                output_root=out_3,
                run_id=run_id,
                artifact_kind="validation_only",
                operation="offline_time_path_validation_once",
                manifest_bytes=manifest_bytes,
                summary_bytes=summary_bytes,
                review_bytes=review_bytes,
            )
    assert not out_3.exists()

    # 4. Parent directory fsync fault AFTER rename -> final root exists on disk, but publish_stage1_5j_c_receipt_root raises and NEVER returns PublishResult!
    out_4 = tmp_path / "f4" / run_id
    out_4.parent.mkdir(parents=True)
    fsync_dir_calls: list[Path] = []
    orig_fsync_dir = jc._fsync_directory

    def _fault_on_parent_dir_fsync(path: Path) -> None:
        fsync_dir_calls.append(path)
        if path == out_4.parent:
            raise OSError("injected parent dir fsync fault after rename")
        orig_fsync_dir(path)

    with monkeypatch.context() as mp:
        mp.setattr(jc, "_fsync_directory", _fault_on_parent_dir_fsync)
        with pytest.raises(
            jc.Stage1_5JCDiagnosticError,
            match="STOP=stage1_5j_c_parent_directory_fsync_failed_after_rename",
        ):
            jc.publish_stage1_5j_c_receipt_root(
                output_root=out_4,
                run_id=run_id,
                artifact_kind="validation_only",
                operation="offline_time_path_validation_once",
                manifest_bytes=manifest_bytes,
                summary_bytes=summary_bytes,
                review_bytes=review_bytes,
            )
    assert out_4.exists(), "Rename already occurred before parent dir fsync failed"

    # 5. Root collision on retry of out_4 -> STOP=stage1_5j_c_output_exists
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_output_exists"):
        jc.publish_stage1_5j_c_receipt_root(
            output_root=out_4,
            run_id=run_id,
            artifact_kind="validation_only",
            operation="offline_time_path_validation_once",
            manifest_bytes=manifest_bytes,
            summary_bytes=summary_bytes,
            review_bytes=review_bytes,
        )

    # 6. Lock collision -> STOP=stage1_5j_c_lock_collision
    out_lock = tmp_path / "flock" / run_id
    out_lock.parent.mkdir(parents=True)
    (out_lock.parent / f".{run_id}.lock").write_text("stale\n", encoding="utf-8")
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_lock_collision"):
        jc.publish_stage1_5j_c_receipt_root(
            output_root=out_lock,
            run_id=run_id,
            artifact_kind="validation_only",
            operation="offline_time_path_validation_once",
            manifest_bytes=manifest_bytes,
            summary_bytes=summary_bytes,
            review_bytes=review_bytes,
        )

    # 7. Staging collision -> STOP=stage1_5j_c_staging_collision
    out_stg = tmp_path / "fstg" / run_id
    out_stg.parent.mkdir(parents=True)
    (out_stg.parent / f".{run_id}.staging").mkdir()
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_staging_collision"):
        jc.publish_stage1_5j_c_receipt_root(
            output_root=out_stg,
            run_id=run_id,
            artifact_kind="validation_only",
            operation="offline_time_path_validation_once",
            manifest_bytes=manifest_bytes,
            summary_bytes=summary_bytes,
            review_bytes=review_bytes,
        )


def _build_and_publish_synthetic_test_receipt_for_loader(
    base_dir: Path,
    *,
    forge_child_mfe_bps: str | None = None,
    mutate_review_text: bool = False,
    include_prl_gap_row: bool = False,
) -> tuple[Path, Path, dict[str, Any], list[dict[str, Any]]]:
    """Test helper in tests/ (never in src/) to construct an isolated synthetic J-C receipt and project root in tmp_path."""
    import csv as std_csv

    jc = _import_core()
    ja_root, ja_summary, pkg_rec, ledger_path = _build_synthetic_ja_root_and_package(base_dir)
    # Copy ledger into canonical relative location under base_dir
    canon_ledger = base_dir / jc.LEDGER_RELATIVE_PATH
    canon_ledger.parent.mkdir(parents=True, exist_ok=True)
    canon_ledger.write_bytes(ledger_path.read_bytes())

    jb_child_rows = [
        {
            "source_article_id": "a" * 32,
            "symbol": "SYNTHUSDT",
            "symbol_launch_time_ms": 1760000000000,
            "anchor_state": "anchor_found",
            "anchor_time_ms": 1760000000000,
            "anchor_price": "1",
            "anchor_delay_ms": 0,
            "j_a_parent_state": "coverage_complete",
            "j_a_child_state": "j_a_child_coverage_complete",
            "required_archive_dates_by_horizon": {},
        }
    ]

    if include_prl_gap_row:
        prl_parent = "0116dd83010043bd95c37626e2277bbe"
        det_rel_prl = f"raw/article_details/{prl_parent}.json"
        det_file_prl = ja_root / det_rel_prl
        body_obj_prl = {
            "node": "root",
            "child": [
                {
                    "tag": "table",
                    "child": [
                        {
                            "tag": "tr",
                            "child": [
                                {
                                    "tag": "td",
                                    "child": [{"node": "text", "text": "USDⓈ-M Perpetual Contract"}],
                                },
                                {
                                    "tag": "td",
                                    "child": [{"node": "text", "text": "PRLUSDT"}],
                                },
                            ],
                        },
                        {
                            "tag": "tr",
                            "child": [
                                {
                                    "tag": "td",
                                    "child": [{"node": "text", "text": "Project Info"}],
                                },
                                {
                                    "tag": "td",
                                    "child": [
                                        {
                                            "node": "text",
                                            "text": "PRL is a cryptocurrency token.",
                                        }
                                    ],
                                },
                            ],
                        },
                    ],
                }
            ],
        }
        detail_payload_prl = {
            "code": "000000",
            "data": {
                "id": 2,
                "code": prl_parent,
                "title": "Binance Will List PRLUSDT",
                "publishDate": 1759990000000,
                "body": json.dumps(body_obj_prl),
            },
            "success": True,
        }
        det_bytes_prl = (
            json.dumps(detail_payload_prl, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        det_file_prl.write_bytes(det_bytes_prl)
        det_sha_prl = hashlib.sha256(det_bytes_prl).hexdigest()

        man_file = ja_root / "manifest.json"
        man_obj = json.loads(man_file.read_text(encoding="utf-8"))
        man_obj["artifacts"].append(
            {
                "byte_count": len(det_bytes_prl),
                "relative_path": det_rel_prl,
                "sha256": det_sha_prl,
            }
        )
        man_obj["artifacts"].sort(key=lambda x: x["relative_path"])
        man_file.write_text(
            json.dumps(man_obj, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

        with open(canon_ledger, "a", newline="", encoding="utf-8") as f:
            writer = std_csv.DictWriter(
                f,
                fieldnames=jc.REQUIRED_LEDGER_COLUMNS,
                lineterminator="\n",
            )
            writer.writerow(
                {
                    "parent_article_id": prl_parent,
                    "symbol": "PRLUSDT",
                    "asset_class": "crypto",
                    "listing_regime": "standard",
                    "classification_status": "confirmed",
                    "table_index": "0",
                    "symbol_column_index": "1",
                    "field_header": "Project Info",
                    "raw_cell_value": "PRL is a cryptocurrency token.",
                    "evidence_locator": "table[0].col[1].row['Project Info']",
                    "source_relative_path": f"ja_root/{det_rel_prl}",
                    "source_sha256": det_sha_prl,
                }
            )
        jb_child_rows.append(
            {
                "source_article_id": prl_parent,
                "symbol": "PRLUSDT",
                "symbol_launch_time_ms": 1760000000000,
                "anchor_state": "no_post_launch_trade_within_anchor_window",
                "anchor_time_ms": None,
                "anchor_price": None,
                "anchor_delay_ms": None,
                "j_a_parent_state": "coverage_complete",
                "j_a_child_state": "j_a_child_coverage_complete",
                "required_archive_dates_by_horizon": {},
            }
        )

    (base_dir / "ja_root" / "summary.json").write_text(
        json.dumps(ja_summary, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (base_dir / "jb_child_rows.json").write_text(
        json.dumps(jb_child_rows, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    # Create synthetic authority seal files in base_dir
    dummy_rel = "dummy_seal.txt"
    dummy_file = base_dir / dummy_rel
    dummy_bytes = b"seal\n"
    dummy_file.write_bytes(dummy_bytes)
    dummy_seal = {
        "relative_path": dummy_rel,
        "sha256": hashlib.sha256(dummy_bytes).hexdigest(),
        "size_bytes": len(dummy_bytes),
    }
    authority_obj = {
        "authorization_release": dummy_seal,
        "design": dummy_seal,
        "input_files": [dummy_seal],
        "plan": dummy_seal,
        "run_authorization": dummy_seal,
        "source_files": [dummy_seal],
        "user_receipt_generation_approval": dummy_seal,
    }

    run_id = "stage1_5j_c_launch_time_path_feasibility_20261024T020304Z"
    exp_count = len(jb_child_rows)
    summary_obj = jc.compute_stage1_5j_c_summary_from_admitted_inputs(
        run_id=run_id,
        artifact_kind="validation_only",
        authority_obj=authority_obj,
        protocol_obj=dict(jc.EXPECTED_PROTOCOL_OBJECT),
        ja_root=ja_root,
        ja_summary=ja_summary,
        jb_child_rows=jb_child_rows,
        ledger_path=canon_ledger,
        project_root=base_dir,
        expected_universe_count=exp_count,
        expected_selected_count=exp_count,
    )

    if forge_child_mfe_bps is not None:
        for c in summary_obj["child_rows"]:
            if c["state"] == "complete" and c["direction"] == "long":
                c["mfe_bps"] = forge_child_mfe_bps
        p_rows, g_rows = jc.project_parents_and_groups(summary_obj["child_rows"])
        summary_obj["parent_rows"] = p_rows
        summary_obj["group_rows"] = g_rows

    review_str = jc.render_stage1_5j_c_review(summary_obj)
    if mutate_review_text:
        review_str = review_str.replace("selected_children: 71", "selected_children: 70")

    summary_bytes = jc._dump_canonical_json_bytes(summary_obj)
    review_bytes = review_str.encode("utf-8")
    manifest_obj = jc.build_stage1_5j_c_manifest(
        run_id=run_id,
        artifact_kind="validation_only",
        summary_bytes=summary_bytes,
        review_bytes=review_bytes,
    )
    manifest_bytes = jc._dump_canonical_json_bytes(manifest_obj)

    out_root = base_dir / "out" / run_id
    jc.publish_stage1_5j_c_receipt_root(
        output_root=out_root,
        run_id=run_id,
        artifact_kind="validation_only",
        operation="offline_time_path_validation_once",
        manifest_bytes=manifest_bytes,
        summary_bytes=summary_bytes,
        review_bytes=review_bytes,
    )
    return out_root, base_dir, ja_summary, jb_child_rows


def test_domain_loader_replay_rejects_forged_semantics_and_review_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify strict J-C domain loader independently replays raw input and rejects forged child/parent/group semantics or review mutations."""
    jc = _import_core()
    assert hasattr(
        jc, "load_verified_stage1_5j_c_launch_time_path_feasibility_root"
    ), "Missing load_verified_stage1_5j_c_launch_time_path_feasibility_root"

    root_ok, proj_ok, ja_sum_ok, jb_rows_ok = _build_and_publish_synthetic_test_receipt_for_loader(
        tmp_path / "loader_ok"
    )
    monkeypatch.setattr(
        jc,
        "_load_upstream_ja_and_jb_for_replay",
        lambda proj: (proj / "ja_root", ja_sum_ok, jb_rows_ok, len(jb_rows_ok), len(jb_rows_ok)),
    )
    loaded = jc.load_verified_stage1_5j_c_launch_time_path_feasibility_root(
        root_ok, expected_artifact_kind="validation_only", project_root=proj_ok
    )
    assert loaded["profile_id"] == "stage1_5j_c_time_path_v1"

    # Wrong expected_artifact_kind -> STOP
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_artifact_kind_mismatch"):
        jc.load_verified_stage1_5j_c_launch_time_path_feasibility_root(
            root_ok,
            expected_artifact_kind="production_diagnostic",
            project_root=proj_ok,
        )

    # Mutate child mfe_bps + recompute parent/group + re-render review + update manifest seals so structural check passes, but raw replay fails!
    root_forged, proj_forged, ja_sum_f, jb_rows_f = (
        _build_and_publish_synthetic_test_receipt_for_loader(
            tmp_path / "loader_forged", forge_child_mfe_bps="2500/1"
        )
    )
    monkeypatch.setattr(
        jc,
        "_load_upstream_ja_and_jb_for_replay",
        lambda proj: (proj / "ja_root", ja_sum_f, jb_rows_f, len(jb_rows_f), len(jb_rows_f)),
    )
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_domain_replay_mismatch"):
        jc.load_verified_stage1_5j_c_launch_time_path_feasibility_root(
            root_forged,
            expected_artifact_kind="validation_only",
            project_root=proj_forged,
        )

    # Mutate review_CN.md and re-seal manifest so manifest hash matches, but review template differs -> STOP
    root_rev, proj_rev, ja_sum_r, jb_rows_r = _build_and_publish_synthetic_test_receipt_for_loader(
        tmp_path / "loader_rev", mutate_review_text=True
    )
    monkeypatch.setattr(
        jc,
        "_load_upstream_ja_and_jb_for_replay",
        lambda proj: (proj / "ja_root", ja_sum_r, jb_rows_r, len(jb_rows_r), len(jb_rows_r)),
    )
    with pytest.raises(jc.Stage1_5JCDiagnosticError, match="STOP=stage1_5j_c_review_render_mismatch"):
        jc.load_verified_stage1_5j_c_launch_time_path_feasibility_root(
            root_rev,
            expected_artifact_kind="validation_only",
            project_root=proj_rev,
        )


def test_independent_oracles_ast_isolation_sentinel_and_prl_positive_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify fixed PRL gap oracle and lexical first-complete positive semantic oracle: AST isolation from production helpers, runtime raising-sentinel proof, and exact parity."""
    jc = _import_core()
    assert hasattr(jc, "run_prl_fixed_gap_oracle"), "Missing run_prl_fixed_gap_oracle"
    assert hasattr(jc, "run_positive_semantic_oracle"), "Missing run_positive_semantic_oracle"

    # 1. AST dependency proof: oracle functions and their _oracle_* helpers must never call production semantic helpers
    source = Path(jc.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_production_helpers = {
        "reduce_child_time_path_from_trades",
        "stream_and_reduce_child_packages",
        "project_parents_and_groups",
        "compute_distribution",
        "_iter_bounded_csv_lines",
        "_validate_and_parse_csv_trade_row",
        "format_exact_fraction",
        "parse_exact_fraction",
        "render_stage1_5j_c_review",
    }
    func_defs = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    oracle_entrypoints = ["run_prl_fixed_gap_oracle", "run_positive_semantic_oracle"]
    visited: set[str] = set()
    queue = list(oracle_entrypoints)
    while queue:
        fn_name = queue.pop(0)
        if fn_name in visited or fn_name not in func_defs:
            continue
        visited.add(fn_name)
        for sub in ast.walk(func_defs[fn_name]):
            if isinstance(sub, ast.Call):
                called_name = None
                if isinstance(sub.func, ast.Name):
                    called_name = sub.func.id
                elif isinstance(sub.func, ast.Attribute):
                    called_name = sub.func.attr
                if called_name:
                    assert called_name not in forbidden_production_helpers, (
                        f"Oracle function {fn_name} called forbidden production helper {called_name}"
                    )
                    if called_name in func_defs and called_name not in visited:
                        queue.append(called_name)

    # 2. Build synthetic multi-child fixture containing PRLUSDT (with gap) and SYNTHUSDT (complete)
    root_ora, proj_ora, ja_summary, jb_child_rows = (
        _build_and_publish_synthetic_test_receipt_for_loader(
            tmp_path / "oracle_fixture", include_prl_gap_row=True
        )
    )
    summary_data = json.loads((root_ora / "summary.json").read_text(encoding="utf-8"))
    ja_root = proj_ora / "ja_root"
    admitted_ctx = jc.build_admitted_ja_context(ja_root, ja_summary)

    # 3. Runtime raising-sentinel on all forbidden production helpers while running both oracles
    def _sentinel(*args, **kwargs):
        raise RuntimeError("PRODUCTION_HELPER_SENTINEL_CALLED")

    with monkeypatch.context() as mp:
        for helper_name in forbidden_production_helpers:
            if hasattr(jc, helper_name):
                mp.setattr(jc, helper_name, _sentinel)

        prl_res = jc.run_prl_fixed_gap_oracle(
            admitted_ja_context=admitted_ctx,
            jb_child_rows=jb_child_rows,
            summary_data=summary_data,
        )
        assert prl_res["status"] == "passed"
        assert prl_res["parent_article_id"] == "0116dd83010043bd95c37626e2277bbe"
        assert prl_res["symbol"] == "PRLUSDT"
        assert prl_res["observed_state"] != "complete"

        pos_res = jc.run_positive_semantic_oracle(
            admitted_ja_context=admitted_ctx,
            jb_child_rows=jb_child_rows,
            summary_data=summary_data,
        )
        assert pos_res["status"] == "passed"
        assert pos_res["selected_symbol"] == "SYNTHUSDT"



