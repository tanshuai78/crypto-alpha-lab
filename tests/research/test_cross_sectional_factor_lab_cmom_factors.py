from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from research.cross_sectional_factor_lab.factors import (
    compute_cmom_14d_skip_1d,
    compute_rebalance_factor_frame,
)


def _rows(symbol: str, start: date, closes: list[float]) -> list[dict]:
    rows = []
    for i, close in enumerate(closes):
        dt = start + timedelta(days=i)
        rows.append({
            "symbol": symbol,
            "date_utc": pd.Timestamp(dt),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "base_volume": 1_000_000.0,
            "quote_volume": 50_000_000.0,
        })
    return rows


def test_cmom_14d_skip_1d_uses_t_minus_1_and_t_minus_15() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 15 + [150.0, 999.0]
    panel = pd.DataFrame(_rows("AAAUSDT", start, closes))

    rebalance_date = pd.Timestamp("2026-01-17")

    assert panel.loc[panel["date_utc"] == pd.Timestamp("2026-01-16"), "close"].item() == 150.0
    assert panel.loc[panel["date_utc"] == pd.Timestamp("2026-01-17"), "close"].item() == 999.0

    result = compute_cmom_14d_skip_1d(panel, "AAAUSDT", rebalance_date)

    assert result == 0.5


def test_cmom_14d_skip_1d_does_not_use_rebalance_day_close() -> None:
    start = date(2026, 1, 1)
    closes = [100.0] * 15 + [100.0, 10_000.0]
    panel = pd.DataFrame(_rows("AAAUSDT", start, closes))

    result = compute_cmom_14d_skip_1d(panel, "AAAUSDT", pd.Timestamp("2026-01-17"))

    assert result == 0.0


def test_cmom_14d_requires_complete_absolute_daily_lookback() -> None:
    start = date(2026, 1, 1)
    rows = _rows("AAAUSDT", start, [100.0] * 17)
    rows = [row for row in rows if row["date_utc"] != pd.Timestamp("2026-01-08")]
    panel = pd.DataFrame(rows)

    result = compute_cmom_14d_skip_1d(panel, "AAAUSDT", pd.Timestamp("2026-01-17"))

    assert result is None


def test_cmom_missing_t_minus_15_returns_none() -> None:
    start = date(2026, 1, 1)
    rows = _rows("AAAUSDT", start, [100.0] * 17)
    rows = [row for row in rows if row["date_utc"] != pd.Timestamp("2026-01-02")]
    panel = pd.DataFrame(rows)

    result = compute_cmom_14d_skip_1d(panel, "AAAUSDT", pd.Timestamp("2026-01-17"))

    assert result is None


def test_cmom_missing_t_minus_1_returns_none() -> None:
    start = date(2026, 1, 1)
    rows = _rows("AAAUSDT", start, [100.0] * 17)
    rows = [row for row in rows if row["date_utc"] != pd.Timestamp("2026-01-16")]
    panel = pd.DataFrame(rows)

    result = compute_cmom_14d_skip_1d(panel, "AAAUSDT", pd.Timestamp("2026-01-17"))

    assert result is None


def test_rebalance_factor_frame_unsupported_factor_name_raises() -> None:
    start = date(2026, 1, 1)
    panel = pd.DataFrame(_rows("AAAUSDT", start, [100.0] * 40))

    try:
        compute_rebalance_factor_frame(panel, pd.Timestamp("2026-02-05"), factor_name="bad_factor")
    except ValueError as exc:
        assert "unsupported factor_name" in str(exc)
    else:
        raise AssertionError("expected unsupported factor_name to raise ValueError")


def test_rebalance_factor_frame_can_compute_cmom_variant() -> None:
    start = date(2026, 1, 1)
    # Need 31+ days so existing 30d liquidity/momentum infrastructure can coexist.
    rows = _rows("AAAUSDT", start, [100.0] * 20 + [120.0] * 20)
    panel = pd.DataFrame(rows)

    factors = compute_rebalance_factor_frame(
        panel,
        pd.Timestamp("2026-02-05"),
        factor_name="cmom_14d_skip_1d",
    )

    assert "cmom_14d_skip_1d" in factors.columns
    assert "momentum_30d_skip_1d" not in factors.columns
    assert len(factors) == 1
