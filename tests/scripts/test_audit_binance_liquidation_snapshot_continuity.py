"""
Tests for audit_binance_liquidation_snapshot_continuity.py

Uses synthetic in-memory data. No real file I/O in unit tests.
"""

import importlib.util
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

SCRIPT_PATH = (
    Path(__file__).parent.parent.parent
    / "scripts"
    / "audit_binance_liquidation_snapshot_continuity.py"
)


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "audit_binance_liquidation_snapshot_continuity", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Module structure
# ---------------------------------------------------------------------------


def test_audit_module_imports():
    mod = _load_audit_module()
    assert hasattr(mod, "build_expected_minute_grid"), "Must export build_expected_minute_grid"
    assert hasattr(mod, "audit_price_continuity"), "Must export audit_price_continuity"
    assert hasattr(mod, "audit_liquidation_file_coverage"), "Must export audit_liquidation_file_coverage"
    assert hasattr(mod, "audit_symbol_month"), "Must export audit_symbol_month"


# ---------------------------------------------------------------------------
# Expected minute grid
# ---------------------------------------------------------------------------


def test_expected_minute_grid_jan_2024():
    mod = _load_audit_module()
    grid = mod.build_expected_minute_grid("2024-01")
    # Jan 2024: 31 days × 1440 min/day = 44640 minutes
    assert len(grid) == 31 * 1440, f"Expected 44640 minutes for Jan, got {len(grid)}"


def test_expected_minute_grid_feb_2024_leap():
    mod = _load_audit_module()
    grid = mod.build_expected_minute_grid("2024-02")
    # 2024 is a leap year: Feb has 29 days
    assert len(grid) == 29 * 1440, f"Expected 29×1440=41760 minutes for Feb 2024 (leap), got {len(grid)}"


def test_expected_minute_grid_mar_2024():
    mod = _load_audit_module()
    grid = mod.build_expected_minute_grid("2024-03")
    assert len(grid) == 31 * 1440


def test_expected_minute_grid_timestamps_are_utc_ms():
    mod = _load_audit_module()
    grid = mod.build_expected_minute_grid("2024-01")
    # First minute of Jan 2024 = 2024-01-01 00:00:00 UTC = 1704067200000
    assert grid[0] == 1704067200000, f"First minute should be 1704067200000, got {grid[0]}"
    # Second minute
    assert grid[1] == 1704067200000 + 60_000


# ---------------------------------------------------------------------------
# audit_price_continuity
# ---------------------------------------------------------------------------


def _make_complete_price_rows(month: str) -> list[dict]:
    """Generate a complete set of 1m kline rows for a month."""
    mod = _load_audit_module()
    grid = mod.build_expected_minute_grid(month)
    return [{"open_time_ms": ts, "close": 50000.0} for ts in grid]


def test_perfect_price_continuity_passes():
    mod = _load_audit_module()
    rows = _make_complete_price_rows("2024-01")
    result = mod.audit_price_continuity(rows, month="2024-01")
    assert result["price_coverage_ratio"] == 1.0
    assert result["price_missing_bucket_count"] == 0
    assert result["price_max_gap_minutes"] == 0
    assert result["price_rows"] == 31 * 1440


def test_price_continuity_with_missing_1_minute():
    mod = _load_audit_module()
    rows = _make_complete_price_rows("2024-01")
    rows_with_gap = [r for r in rows if r["open_time_ms"] != rows[100]["open_time_ms"]]
    result = mod.audit_price_continuity(rows_with_gap, month="2024-01")
    assert result["price_missing_bucket_count"] == 1
    assert result["price_max_gap_minutes"] == 1
    assert result["price_coverage_ratio"] < 1.0


def test_price_continuity_fails_with_large_gap():
    mod = _load_audit_module()
    rows = _make_complete_price_rows("2024-01")
    # Remove 2 consecutive minutes → gap = 2 minutes
    ts_to_remove = {rows[500]["open_time_ms"], rows[501]["open_time_ms"]}
    rows_gap = [r for r in rows if r["open_time_ms"] not in ts_to_remove]
    result = mod.audit_price_continuity(rows_gap, month="2024-01")
    assert result["price_max_gap_minutes"] == 2


def test_price_coverage_ratio_calculation():
    mod = _load_audit_module()
    rows = _make_complete_price_rows("2024-01")
    total = len(rows)
    # Remove 100 rows
    rows_partial = rows[:total - 100]
    result = mod.audit_price_continuity(rows_partial, month="2024-01")
    # Coverage = present / expected
    expected_ratio = (total - 100) / total
    assert abs(result["price_coverage_ratio"] - expected_ratio) < 0.001


# ---------------------------------------------------------------------------
# audit_liquidation_file_coverage
# ---------------------------------------------------------------------------


def test_full_liquidation_file_coverage_passes():
    mod = _load_audit_module()
    # Jan 2024: 31 days
    all_days = [f"2024-01-{d:02d}" for d in range(1, 32)]
    result = mod.audit_liquidation_file_coverage(
        files_found=all_days,
        month="2024-01",
    )
    assert result["liquidation_files_found"] == 31
    assert result["liquidation_files_expected"] == 31
    assert result["liquidation_file_coverage_ratio"] == 1.0


def test_partial_liquidation_file_coverage():
    mod = _load_audit_module()
    # Only 20 of 31 days
    some_days = [f"2024-01-{d:02d}" for d in range(1, 21)]
    result = mod.audit_liquidation_file_coverage(
        files_found=some_days,
        month="2024-01",
    )
    assert result["liquidation_files_found"] == 20
    assert result["liquidation_files_expected"] == 31
    assert abs(result["liquidation_file_coverage_ratio"] - 20 / 31) < 0.001


def test_zero_liquidation_rows_but_full_daily_files_still_passes_file_coverage():
    """
    A month with zero liquidation rows (no events fired) but all daily files
    present must still pass the file coverage gate.
    """
    mod = _load_audit_module()
    all_days = [f"2024-01-{d:02d}" for d in range(1, 32)]
    result = mod.audit_liquidation_file_coverage(
        files_found=all_days,
        month="2024-01",
    )
    assert result["liquidation_file_coverage_ratio"] == 1.0


# ---------------------------------------------------------------------------
# audit_symbol_month — integrated
# ---------------------------------------------------------------------------


def test_audit_symbol_month_required_output_keys():
    mod = _load_audit_module()
    price_rows = _make_complete_price_rows("2024-01")
    all_days = [f"2024-01-{d:02d}" for d in range(1, 32)]
    liq_rows = []  # Sparse — no events

    result = mod.audit_symbol_month(
        symbol="BTCUSDT",
        month="2024-01",
        price_rows=price_rows,
        liquidation_files_found=all_days,
        liquidation_rows=liq_rows,
    )

    required_keys = {
        "price_coverage_ratio",
        "price_missing_bucket_count",
        "price_max_gap_minutes",
        "price_rows",
        "liquidation_files_found",
        "liquidation_files_expected",
        "liquidation_file_coverage_ratio",
        "liquidation_snapshot_rows",
        "zero_filled_liquidation_minutes",
        "dataset_rows",
        "joined_rows",
        "passes_continuity_gate",
    }
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"


def test_perfect_data_passes_continuity_gate():
    mod = _load_audit_module()
    price_rows = _make_complete_price_rows("2024-01")
    all_days = [f"2024-01-{d:02d}" for d in range(1, 32)]
    liq_rows = []

    result = mod.audit_symbol_month(
        symbol="BTCUSDT",
        month="2024-01",
        price_rows=price_rows,
        liquidation_files_found=all_days,
        liquidation_rows=liq_rows,
    )
    assert result["passes_continuity_gate"] is True


def test_sparse_liquidation_rows_does_not_fail_continuity():
    """
    Sparse liquidation minutes (many zeros) must NOT fail the continuity gate.
    Only price continuity and file availability determine the gate.
    """
    mod = _load_audit_module()
    price_rows = _make_complete_price_rows("2024-01")
    all_days = [f"2024-01-{d:02d}" for d in range(1, 32)]
    # Only 5 actual liquidation events
    liq_rows = [
        {"timestamp_ms": 1704067200000 + i * 3600_000, "side": "long", "notional_usdt": 1_000_000.0}
        for i in range(5)
    ]

    result = mod.audit_symbol_month(
        symbol="BTCUSDT",
        month="2024-01",
        price_rows=price_rows,
        liquidation_files_found=all_days,
        liquidation_rows=liq_rows,
    )
    assert result["passes_continuity_gate"] is True
    # Most minutes should be zero-filled
    assert result["zero_filled_liquidation_minutes"] > 0


def test_failed_price_coverage_fails_gate():
    """Price coverage below 0.99 must fail the gate."""
    mod = _load_audit_module()
    price_rows = _make_complete_price_rows("2024-01")
    # Keep only 90% of rows → coverage 0.90 < 0.99 threshold
    total = len(price_rows)
    truncated = price_rows[: int(total * 0.90)]
    all_days = [f"2024-01-{d:02d}" for d in range(1, 32)]

    result = mod.audit_symbol_month(
        symbol="BTCUSDT",
        month="2024-01",
        price_rows=truncated,
        liquidation_files_found=all_days,
        liquidation_rows=[],
    )
    assert result["passes_continuity_gate"] is False


def test_failed_liquidation_file_coverage_fails_gate():
    """File coverage < 1.0 (missing daily files) must fail the gate."""
    mod = _load_audit_module()
    price_rows = _make_complete_price_rows("2024-01")
    # Only half the daily files present
    partial_days = [f"2024-01-{d:02d}" for d in range(1, 16)]

    result = mod.audit_symbol_month(
        symbol="BTCUSDT",
        month="2024-01",
        price_rows=price_rows,
        liquidation_files_found=partial_days,
        liquidation_rows=[],
    )
    assert result["passes_continuity_gate"] is False


def test_joined_rows_equals_price_grid_size():
    """After zero-filling, joined_rows must equal the full price grid size."""
    mod = _load_audit_module()
    price_rows = _make_complete_price_rows("2024-01")
    all_days = [f"2024-01-{d:02d}" for d in range(1, 32)]

    result = mod.audit_symbol_month(
        symbol="BTCUSDT",
        month="2024-01",
        price_rows=price_rows,
        liquidation_files_found=all_days,
        liquidation_rows=[],
    )
    assert result["joined_rows"] == 31 * 1440
    assert result["dataset_rows"] == 31 * 1440
