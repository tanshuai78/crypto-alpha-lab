from __future__ import annotations

import pandas as pd
import pytest

from research.cross_sectional_factor_lab.panel import forward_fill_close_by_symbol, load_daily_panel


def test_load_daily_panel_normalizes_schema_and_sorts() -> None:
    rows = [
        {"symbol": "bbb/usdt", "date_utc": "2026-01-02", "open": 2, "high": 3, "low": 1, "close": 2, "base_volume": 1, "quote_volume": 30_000_000},
        {"symbol": "AAA/USDT", "date_utc": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 1, "base_volume": 1, "quote_volume": 25_000_000},
    ]

    panel = load_daily_panel(rows)

    assert list(panel.columns) == [
        "symbol",
        "date_utc",
        "open",
        "high",
        "low",
        "close",
        "base_volume",
        "quote_volume",
    ]
    assert panel.iloc[0]["symbol"] == "AAAUSDT"
    assert panel.iloc[0]["date_utc"] == pd.Timestamp("2026-01-01")


def test_load_daily_panel_rejects_non_positive_close() -> None:
    rows = [{"symbol": "AAAUSDT", "date_utc": "2026-01-01", "open": 1, "high": 1, "low": 1, "close": 0, "base_volume": 1, "quote_volume": 1}]

    with pytest.raises(ValueError, match="close"):
        load_daily_panel(rows)


def test_forward_fill_close_by_symbol_does_not_cross_symbols() -> None:
    panel = pd.DataFrame(
        [
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-01-01"), "close": 100.0},
            {"symbol": "AAAUSDT", "date_utc": pd.Timestamp("2026-01-02"), "close": None},
            {"symbol": "BBBUSDT", "date_utc": pd.Timestamp("2026-01-01"), "close": 200.0},
            {"symbol": "BBBUSDT", "date_utc": pd.Timestamp("2026-01-02"), "close": None},
        ]
    )

    filled, ffill_count = forward_fill_close_by_symbol(panel)

    assert ffill_count == 2
    assert filled.loc[filled["symbol"] == "AAAUSDT", "close"].iloc[-1] == 100.0
    assert filled.loc[filled["symbol"] == "BBBUSDT", "close"].iloc[-1] == 200.0
