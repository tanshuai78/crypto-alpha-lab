from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from research.cross_sectional_factor_lab.factors import (
    compute_momentum_30d_skip_1d,
    compute_rebalance_factor_frame,
)


def _rows(symbol: str, start: date, closes: list[float], quote_volume: float = 25_000_000.0) -> list[dict]:
    return [
        {
            "symbol": symbol,
            "date_utc": start + timedelta(days=i),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "base_volume": 1.0,
            "quote_volume": quote_volume,
        }
        for i, close in enumerate(closes)
    ]


def test_momentum_30d_skip_1d_uses_t_minus_1_and_t_minus_31() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 31 + [150.0, 999.0]
    panel = pd.DataFrame(_rows("AAAUSDT", start, closes))
    panel["date_utc"] = pd.to_datetime(panel["date_utc"])

    assert panel.loc[panel["date_utc"] == pd.Timestamp("2026-02-01"), "close"].item() == 150.0
    assert panel.loc[panel["date_utc"] == pd.Timestamp("2026-02-02"), "close"].item() == 999.0

    result = compute_momentum_30d_skip_1d(
        panel=panel,
        symbol="AAAUSDT",
        rebalance_date=pd.Timestamp("2026-02-02"),
    )

    assert result == pytest.approx(0.5)


def test_momentum_does_not_use_rebalance_day_close() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 31 + [150.0, 10_000.0]
    panel = pd.DataFrame(_rows("AAAUSDT", start, closes))
    panel["date_utc"] = pd.to_datetime(panel["date_utc"])

    result = compute_momentum_30d_skip_1d(
        panel=panel,
        symbol="AAAUSDT",
        rebalance_date=pd.Timestamp("2026-02-02"),
    )

    assert result == pytest.approx(0.5)


def test_momentum_requires_31_prior_daily_bars() -> None:
    panel = pd.DataFrame(_rows("AAAUSDT", date(2026, 1, 1), [100.0] * 30))
    panel["date_utc"] = pd.to_datetime(panel["date_utc"])

    result = compute_momentum_30d_skip_1d(
        panel=panel,
        symbol="AAAUSDT",
        rebalance_date=pd.Timestamp("2026-01-31"),
    )

    assert result is None


def test_rebalance_factor_frame_applies_point_in_time_liquidity_gate() -> None:
    start = date(2026, 1, 1)
    panel = pd.DataFrame(
        _rows("AAAUSDT", start, [100.0] * 31 + [150.0], quote_volume=25_000_000.0)
        + _rows("BBBUSDT", start, [100.0] * 31 + [160.0], quote_volume=1_000_000.0)
    )
    panel["date_utc"] = pd.to_datetime(panel["date_utc"])

    frame = compute_rebalance_factor_frame(panel=panel, rebalance_date=pd.Timestamp("2026-02-01"))

    assert set(frame["symbol"]) == {"AAAUSDT"}


def test_late_listed_symbol_is_excluded_until_it_has_required_lookback() -> None:
    start = date(2026, 1, 1)
    mature = _rows("AAAUSDT", start, [100.0] * 31 + [150.0], quote_volume=25_000_000.0)
    late = _rows("LATEUSDT", date(2026, 1, 20), [100.0] * 10 + [200.0], quote_volume=25_000_000.0)
    panel = pd.DataFrame(mature + late)
    panel["date_utc"] = pd.to_datetime(panel["date_utc"])

    frame = compute_rebalance_factor_frame(panel=panel, rebalance_date=pd.Timestamp("2026-02-01"))

    assert "AAAUSDT" in set(frame["symbol"])
    assert "LATEUSDT" not in set(frame["symbol"])


def test_symbol_missing_one_lookback_day_is_excluded() -> None:
    start = date(2026, 1, 1)
    rows = _rows("AAAUSDT", start, [100.0] * 31 + [150.0], quote_volume=25_000_000.0)
    rows = [row for row in rows if row["date_utc"] != date(2026, 1, 2)]
    panel = pd.DataFrame(rows)
    panel["date_utc"] = pd.to_datetime(panel["date_utc"])

    frame = compute_rebalance_factor_frame(panel=panel, rebalance_date=pd.Timestamp("2026-02-01"))

    assert "AAAUSDT" not in set(frame["symbol"])


def test_liquidity_rolling_window_requires_30_prior_days() -> None:
    panel = pd.DataFrame(_rows("AAAUSDT", date(2026, 1, 15), [100.0] * 20, quote_volume=25_000_000.0))
    panel["date_utc"] = pd.to_datetime(panel["date_utc"])

    frame = compute_rebalance_factor_frame(panel=panel, rebalance_date=pd.Timestamp("2026-02-01"))

    assert frame.empty
