from __future__ import annotations

import pytest

from research.external_signal_shadow.stage1_3_models import (
    HistoricalBar,
    compute_bar_coverage,
    find_duplicate_bar_starts,
)

MS_15M = 15 * 60 * 1000


def test_historical_bar_requires_complete_positive_ohlcv() -> None:
    bar = HistoricalBar(
        symbol="BTC_USDT",
        bar_start_ms=1_000,
        bar_end_ms=1_000 + MS_15M,
        open_price=100.0,
        high_price=110.0,
        low_price=90.0,
        close_price=105.0,
        quote_volume=1_000_000.0,
    )
    assert bar.symbol == "BTCUSDT"


def test_historical_bar_rejects_invalid_end_time() -> None:
    with pytest.raises(ValueError, match="bar_end_ms"):
        HistoricalBar("BTCUSDT", 1_000, 1_000, 1, 1, 1, 1, 1)


def test_historical_bar_rejects_inconsistent_ohlc() -> None:
    with pytest.raises(ValueError, match="high_price"):
        HistoricalBar("BTCUSDT", 0, MS_15M, 100, 99, 90, 100, 1)
    with pytest.raises(ValueError, match="low_price"):
        HistoricalBar("BTCUSDT", 0, MS_15M, 100, 110, 101, 100, 1)


def test_historical_bar_rejects_wrong_duration() -> None:
    with pytest.raises(ValueError, match="15m duration"):
        HistoricalBar("BTCUSDT", 0, 2 * MS_15M, 100, 100, 100, 100, 1)


def test_bar_coverage_ratio_counts_missing_15m_slots() -> None:
    bars = [
        HistoricalBar("BTCUSDT", 0, MS_15M, 1, 1, 1, 1, 1),
        HistoricalBar("BTCUSDT", MS_15M, 2 * MS_15M, 1, 1, 1, 1, 1),
        HistoricalBar("BTCUSDT", 3 * MS_15M, 4 * MS_15M, 1, 1, 1, 1, 1),
    ]
    coverage = compute_bar_coverage(bars, interval_ms=MS_15M)
    assert coverage["BTCUSDT"] == 0.75


def test_duplicate_bar_starts_are_reported_by_symbol() -> None:
    bars = [
        HistoricalBar("BTCUSDT", 0, MS_15M, 1, 1, 1, 1, 1),
        HistoricalBar("BTCUSDT", 0, MS_15M, 1, 1, 1, 1, 1),
        HistoricalBar("ETHUSDT", MS_15M, 2 * MS_15M, 1, 1, 1, 1, 1),
    ]

    duplicates = find_duplicate_bar_starts(bars)

    assert duplicates == {"BTCUSDT": [0]}


def test_bar_coverage_uses_unique_bar_starts() -> None:
    bars = [
        HistoricalBar("BTCUSDT", 0, MS_15M, 1, 1, 1, 1, 1),
        HistoricalBar("BTCUSDT", 0, MS_15M, 1, 1, 1, 1, 1),
        HistoricalBar("BTCUSDT", MS_15M, 2 * MS_15M, 1, 1, 1, 1, 1),
    ]

    coverage = compute_bar_coverage(bars, interval_ms=MS_15M)

    assert coverage["BTCUSDT"] == 1.0
