"""
Tests for build_binance_liquidation_snapshot_event_dataset.py

Uses synthetic in-memory data. No real file I/O.
"""

import sys
import os
import importlib.util
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

SCRIPT_PATH = (
    Path(__file__).parent.parent.parent
    / "scripts"
    / "build_binance_liquidation_snapshot_event_dataset.py"
)


def _load_builder_module():
    spec = importlib.util.spec_from_file_location(
        "build_binance_liquidation_snapshot_event_dataset", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -------------------------------------------------------------------------
# Helpers: synthetic data generators
# -------------------------------------------------------------------------

_MS_PER_MIN = 60_000
_JAN_2024_START_MS = 1_704_067_200_000  # 2024-01-01 00:00:00 UTC


def _make_price_rows(start_ms: int, count: int, base_price: float = 50000.0) -> list[dict]:
    return [
        {
            "open_time_ms": start_ms + i * _MS_PER_MIN,
            "open_price": base_price,
            "close_price": base_price,
        }
        for i in range(count)
    ]


def _make_liq_rows(start_ms: int, count: int, side: str = "long", notional: float = 5_000_000.0) -> list[dict]:
    return [
        {
            "timestamp_ms": start_ms + i * _MS_PER_MIN * 100,
            "side": side,
            "notional_usdt": notional,
        }
        for i in range(count)
    ]


# -------------------------------------------------------------------------
# Module structure
# -------------------------------------------------------------------------


def test_builder_module_imports():
    mod = _load_builder_module()
    assert hasattr(mod, "build_aligned_rows"), "Must export build_aligned_rows"
    assert hasattr(mod, "build_dataset"), "Must export build_dataset"


# -------------------------------------------------------------------------
# build_aligned_rows — row shape
# -------------------------------------------------------------------------


def test_build_aligned_rows_returns_required_fields():
    mod = _load_builder_module()
    price_rows = _make_price_rows(_JAN_2024_START_MS, 1500)
    liq_rows = _make_liq_rows(_JAN_2024_START_MS, 3)
    result = mod.build_aligned_rows(
        symbol="BTCUSDT",
        price_rows=price_rows,
        liquidation_rows=liq_rows,
    )
    assert len(result) > 0
    for row in result[:5]:
        assert "symbol" in row
        assert "bar_start_ms" in row
        assert "long_liquidation_notional_1m_usdt" in row
        assert "short_liquidation_notional_1m_usdt" in row
        assert "open_price" in row
        assert "close_price" in row


def test_build_aligned_rows_symbol_preserved():
    mod = _load_builder_module()
    price_rows = _make_price_rows(_JAN_2024_START_MS, 100)
    result = mod.build_aligned_rows(
        symbol="ETHUSDT",
        price_rows=price_rows,
        liquidation_rows=[],
    )
    for row in result:
        assert row["symbol"] == "ETHUSDT"


def test_build_aligned_rows_zero_fills_missing_liq():
    """Minutes without liquidation events must have notional=0."""
    mod = _load_builder_module()
    price_rows = _make_price_rows(_JAN_2024_START_MS, 500)
    liq_rows = []  # No liquidation events
    result = mod.build_aligned_rows(
        symbol="BTCUSDT",
        price_rows=price_rows,
        liquidation_rows=liq_rows,
    )
    for row in result:
        assert row["long_liquidation_notional_1m_usdt"] == 0.0
        assert row["short_liquidation_notional_1m_usdt"] == 0.0


def test_build_aligned_rows_assigns_liq_to_correct_minute():
    mod = _load_builder_module()
    price_rows = _make_price_rows(_JAN_2024_START_MS, 500)
    # Single long liq event at minute 10
    target_ms = _JAN_2024_START_MS + 10 * _MS_PER_MIN
    liq_rows = [{"timestamp_ms": target_ms, "side": "long", "notional_usdt": 9_000_000.0}]
    result = mod.build_aligned_rows(
        symbol="BTCUSDT",
        price_rows=price_rows,
        liquidation_rows=liq_rows,
    )
    by_ts = {r["bar_start_ms"]: r for r in result}
    assert by_ts[target_ms]["long_liquidation_notional_1m_usdt"] == 9_000_000.0
    assert by_ts[target_ms]["short_liquidation_notional_1m_usdt"] == 0.0


# -------------------------------------------------------------------------
# build_dataset — cross-month concatenation
# -------------------------------------------------------------------------


def test_build_dataset_concatenates_months():
    """Dataset must combine all months into one continuous time-series per symbol."""
    mod = _load_builder_module()
    # 3 months × 1500 rows each
    month_data = {
        "2024-01": {
            "price_rows": _make_price_rows(_JAN_2024_START_MS, 1500),
            "liq_rows": [],
        },
        "2024-02": {
            "price_rows": _make_price_rows(_JAN_2024_START_MS + 31 * 1440 * _MS_PER_MIN, 1500),
            "liq_rows": [],
        },
        "2024-03": {
            "price_rows": _make_price_rows(_JAN_2024_START_MS + 60 * 1440 * _MS_PER_MIN, 1500),
            "liq_rows": [],
        },
    }
    result = mod.build_dataset(
        symbol="BTCUSDT",
        month_data=month_data,
        passed_months=["2024-01", "2024-02", "2024-03"],
    )
    # All 3 × 1500 rows should be concatenated and sorted
    assert len(result) == 3 * 1500


def test_build_dataset_excludes_failed_months():
    """Symbol-months that fail continuity must be excluded from the dataset."""
    mod = _load_builder_module()
    month_data = {
        "2024-01": {
            "price_rows": _make_price_rows(_JAN_2024_START_MS, 1500),
            "liq_rows": [],
        },
        "2024-02": {
            "price_rows": _make_price_rows(_JAN_2024_START_MS + 31 * 1440 * _MS_PER_MIN, 1500),
            "liq_rows": [],
        },
    }
    # Only 2024-01 passed continuity
    result = mod.build_dataset(
        symbol="BTCUSDT",
        month_data=month_data,
        passed_months=["2024-01"],
    )
    assert len(result) == 1500


def test_build_dataset_sorted_ascending_by_bar_start_ms():
    mod = _load_builder_module()
    month_data = {
        "2024-01": {
            "price_rows": _make_price_rows(_JAN_2024_START_MS, 1500),
            "liq_rows": [],
        },
        "2024-02": {
            "price_rows": _make_price_rows(_JAN_2024_START_MS + 31 * 1440 * _MS_PER_MIN, 1500),
            "liq_rows": [],
        },
    }
    result = mod.build_dataset(
        symbol="BTCUSDT",
        month_data=month_data,
        passed_months=["2024-01", "2024-02"],
    )
    timestamps = [r["bar_start_ms"] for r in result]
    assert timestamps == sorted(timestamps), "Dataset must be sorted ascending by bar_start_ms"


def test_build_dataset_preserves_1m_shock_semantics():
    """
    The dataset must not artificially lose the first 24h of the next month.
    The first 1440 rows of 2024-02 must be present when 2024-02 passes continuity.
    """
    mod = _load_builder_module()
    feb_start_ms = _JAN_2024_START_MS + 31 * 1440 * _MS_PER_MIN
    month_data = {
        "2024-01": {
            "price_rows": _make_price_rows(_JAN_2024_START_MS, 1440),
            "liq_rows": [],
        },
        "2024-02": {
            "price_rows": _make_price_rows(feb_start_ms, 1440),
            "liq_rows": [],
        },
    }
    result = mod.build_dataset(
        symbol="BTCUSDT",
        month_data=month_data,
        passed_months=["2024-01", "2024-02"],
    )
    # The first row of Feb must be present
    feb_first_ts = feb_start_ms
    row_timestamps = {r["bar_start_ms"] for r in result}
    assert feb_first_ts in row_timestamps, "First minute of 2024-02 must not be dropped"


def test_build_dataset_response_excludes_shock_minute_bar():
    """
    Verify that the dataset preserves the convention that response is measured
    starting from M+1 (the bar containing the shock minute is excluded from response).
    This is structural: the dataset rows must have both open_price and close_price
    so the response_map can compute entry at M+1 open and exit at M+{horizon} close.
    """
    mod = _load_builder_module()
    price_rows = _make_price_rows(_JAN_2024_START_MS, 100)
    liq_rows = [{"timestamp_ms": _JAN_2024_START_MS, "side": "long", "notional_usdt": 5_000_000.0}]
    result = mod.build_aligned_rows(
        symbol="BTCUSDT",
        price_rows=price_rows,
        liquidation_rows=liq_rows,
    )
    # Rows must carry open_price and close_price for the response_map to function
    for row in result[:5]:
        assert "open_price" in row, "open_price must be present for response_map entry"
        assert "close_price" in row, "close_price must be present for response_map exit"
