from __future__ import annotations

from datetime import timedelta

import pandas as pd

import configs.base as cfg

REQUIRED_FACTOR_COLUMNS = (
    "symbol",
    "momentum_30d_skip_1d",
    "rolling_30d_median_quote_volume_usdt",
    "signal_asof_date",
    "lookback_start_date",
    "eligible_for_rank"
)


def compute_momentum_30d_skip_1d(
    panel: pd.DataFrame, symbol: str, rebalance_date: pd.Timestamp
) -> float | None:
    # Filter for symbol
    symbol_data = panel[panel["symbol"] == symbol]
    if symbol_data.empty:
        return None

    # Calculate exact target dates
    skip_days = cfg.FACTOR_LAB_STAGEA_SKIP_RECENT_DAYS
    lookback_days = cfg.FACTOR_LAB_STAGEA_MOMENTUM_LOOKBACK_DAYS

    signal_asof_date = rebalance_date - timedelta(days=skip_days)
    lookback_start_date = rebalance_date - timedelta(days=skip_days + lookback_days)

    # Use absolute date lookup
    asof_rows = symbol_data[symbol_data["date_utc"] == signal_asof_date]
    start_rows = symbol_data[symbol_data["date_utc"] == lookback_start_date]

    if asof_rows.empty or start_rows.empty:
        return None

    close_asof = float(asof_rows["close"].iloc[0])
    close_start = float(start_rows["close"].iloc[0])

    if close_start <= 0:
        return None

    # Check if there are missing days in between to ensure full lookback coverage
    # Total expected days between lookback_start_date and signal_asof_date (inclusive) is lookback_days + 1
    # For lookback_days = 30, it is 31 days.
    expected_days = lookback_days + 1
    actual_days = symbol_data[
        (symbol_data["date_utc"] >= lookback_start_date)
        & (symbol_data["date_utc"] <= signal_asof_date)
    ]["date_utc"].nunique()

    if actual_days < expected_days:
        return None

    return (close_asof / close_start) - 1.0


def compute_rebalance_factor_frame(
    panel: pd.DataFrame, rebalance_date: pd.Timestamp
) -> pd.DataFrame:
    # 30d liquidity window: from rebalance_date - 30 days to rebalance_date - 1 day
    liq_start = rebalance_date - timedelta(days=30)
    liq_end = rebalance_date - timedelta(days=1)

    # Filter panel for symbols and date range
    sub_panel = panel[(panel["date_utc"] >= liq_start) & (panel["date_utc"] <= liq_end)]
    if sub_panel.empty:
        return pd.DataFrame(columns=list(REQUIRED_FACTOR_COLUMNS))

    records = []
    symbols = sub_panel["symbol"].unique()

    # Get thresholds
    min_volume = cfg.FACTOR_LAB_STAGEA_MIN_30D_MEDIAN_QUOTE_VOLUME_USDT

    for symbol in symbols:
        symbol_sub = sub_panel[sub_panel["symbol"] == symbol]

        # Enforce that symbol must have exactly 30 days in the liquidity window
        if symbol_sub["date_utc"].nunique() < 30:
            continue

        # Compute median quote volume
        median_vol = float(symbol_sub["quote_volume"].median())
        if median_vol < min_volume:
            continue

        # Compute momentum (which requires 31 days: rebalance_date - 31 to rebalance_date - 1)
        mom = compute_momentum_30d_skip_1d(panel, symbol, rebalance_date)
        if mom is None:
            continue

        records.append({
            "symbol": symbol,
            "momentum_30d_skip_1d": mom,
            "rolling_30d_median_quote_volume_usdt": median_vol,
            "signal_asof_date": rebalance_date - timedelta(days=1),
            "lookback_start_date": rebalance_date - timedelta(days=31),
            "eligible_for_rank": True
        })

    if not records:
        return pd.DataFrame(columns=list(REQUIRED_FACTOR_COLUMNS))

    return pd.DataFrame(records)
