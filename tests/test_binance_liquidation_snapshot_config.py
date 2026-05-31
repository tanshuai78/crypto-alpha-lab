"""
Tests that all required Binance liquidation snapshot constants exist in configs/base.py
with sane types and valid values.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import configs.base as cfg


# ---------------------------------------------------------------------------
# Existence and type tests
# ---------------------------------------------------------------------------


def test_symbols_is_tuple_of_strings():
    syms = cfg.BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS
    assert isinstance(syms, (tuple, list)), "BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS must be a tuple/list"
    assert len(syms) > 0, "BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS must be non-empty"
    for s in syms:
        assert isinstance(s, str), f"Each symbol must be a string, got {type(s)}"


def test_months_is_tuple_of_strings():
    months = cfg.BINANCE_LIQUIDATION_SNAPSHOT_MONTHS
    assert isinstance(months, (tuple, list))
    assert len(months) > 0
    for m in months:
        assert isinstance(m, str)
        # Expect YYYY-MM format
        parts = m.split("-")
        assert len(parts) == 2, f"Month must be YYYY-MM format, got {m}"
        assert len(parts[0]) == 4
        assert len(parts[1]) == 2


def test_raw_dir_is_string():
    assert isinstance(cfg.BINANCE_LIQUIDATION_SNAPSHOT_RAW_DIR, str)
    assert len(cfg.BINANCE_LIQUIDATION_SNAPSHOT_RAW_DIR) > 0


def test_extracted_dir_is_string():
    assert isinstance(cfg.BINANCE_LIQUIDATION_SNAPSHOT_EXTRACTED_DIR, str)
    assert len(cfg.BINANCE_LIQUIDATION_SNAPSHOT_EXTRACTED_DIR) > 0


def test_processed_dir_is_string():
    assert isinstance(cfg.BINANCE_LIQUIDATION_SNAPSHOT_PROCESSED_DIR, str)
    assert len(cfg.BINANCE_LIQUIDATION_SNAPSHOT_PROCESSED_DIR) > 0


def test_continuity_min_coverage_ratio_in_range():
    ratio = cfg.BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MIN_COVERAGE_RATIO
    assert isinstance(ratio, float), f"Expected float, got {type(ratio)}"
    assert 0.0 < ratio <= 1.0, f"Coverage ratio must be in (0, 1], got {ratio}"


def test_continuity_max_gap_minutes_is_positive_int():
    gap = cfg.BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MAX_GAP_MINUTES
    assert isinstance(gap, int), f"Expected int, got {type(gap)}"
    assert gap >= 1, f"Max gap must be >= 1 minute, got {gap}"


def test_min_total_events_is_positive_int():
    total = cfg.BINANCE_LIQUIDATION_SNAPSHOT_MIN_TOTAL_EVENTS
    assert isinstance(total, int)
    assert total >= 1


def test_min_events_per_month_is_positive_int():
    per_month = cfg.BINANCE_LIQUIDATION_SNAPSHOT_MIN_EVENTS_PER_MONTH
    assert isinstance(per_month, int)
    assert per_month >= 1


# ---------------------------------------------------------------------------
# Value sanity tests
# ---------------------------------------------------------------------------


def test_default_symbols_include_btc_and_eth():
    syms = cfg.BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS
    assert "BTC/USDT" in syms
    assert "ETH/USDT" in syms


def test_default_months_cover_q1_2024():
    months = cfg.BINANCE_LIQUIDATION_SNAPSHOT_MONTHS
    assert "2024-01" in months
    assert "2024-02" in months
    assert "2024-03" in months


def test_continuity_threshold_is_strict():
    # The plan requires 0.99
    ratio = cfg.BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MIN_COVERAGE_RATIO
    assert ratio >= 0.99, f"Expected >= 0.99 strict gate, got {ratio}"


def test_max_gap_is_one_minute():
    # Price continuity must satisfy max_gap_minutes <= 1
    gap = cfg.BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MAX_GAP_MINUTES
    assert gap == 1, f"Expected exactly 1 minute max gap, got {gap}"
