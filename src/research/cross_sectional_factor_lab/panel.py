from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

from research.cross_sectional_factor_lab.universe import normalize_symbol

REQUIRED_DAILY_COLUMNS = (
    "symbol",
    "date_utc",
    "open",
    "high",
    "low",
    "close",
    "base_volume",
    "quote_volume",
)


def load_daily_panel(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows))
    if frame.empty:
        # Return empty dataframe with correct schema
        return pd.DataFrame(columns=list(REQUIRED_DAILY_COLUMNS))

    missing = [col for col in REQUIRED_DAILY_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"missing daily panel columns: {missing}")

    frame = frame.loc[:, list(REQUIRED_DAILY_COLUMNS)].copy()
    frame["symbol"] = frame["symbol"].map(normalize_symbol)
    frame["date_utc"] = pd.to_datetime(frame["date_utc"], utc=False)

    for col in ("open", "high", "low", "close", "base_volume", "quote_volume"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    # If any OHLC is NaN, raise error
    if frame[["open", "high", "low", "close"]].isna().any().any():
        raise ValueError("daily panel contains non-numeric OHLC values")
    if (frame["close"] <= 0).any():
        raise ValueError("daily panel contains non-positive close values")

    frame = frame.sort_values(["symbol", "date_utc"]).reset_index(drop=True)
    return frame


def forward_fill_close_by_symbol(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if frame.empty:
        return frame.copy(), 0
    result = frame.sort_values(["symbol", "date_utc"]).copy()
    before = result["close"].isna().sum()
    result["close"] = result.groupby("symbol")["close"].ffill()
    after = result["close"].isna().sum()
    return result, int(before - after)
