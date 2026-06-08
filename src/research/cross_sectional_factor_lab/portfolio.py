from __future__ import annotations

from collections.abc import Iterable
import pandas as pd

import configs.base as cfg


def eligible_monday_rebalance_dates(dates: Iterable[pd.Timestamp]) -> list[pd.Timestamp]:
    sorted_dates = sorted(list(set(pd.to_datetime(d) for d in dates)))
    if not sorted_dates:
        return []

    first_date = sorted_dates[0]
    warmup_days = max(
        cfg.FACTOR_LAB_STAGEA_MOMENTUM_LOOKBACK_DAYS
        + cfg.FACTOR_LAB_STAGEA_SKIP_RECENT_DAYS,
        30,
    )

    rebalances = []
    for dt in sorted_dates:
        # Check weekday matches config (0 is Monday)
        if dt.weekday() != cfg.FACTOR_LAB_STAGEA_REBALANCE_WEEKDAY_UTC:
            continue
        # Check if warmup days are satisfied
        if (dt - first_date).days >= warmup_days:
            rebalances.append(dt)

    return rebalances


def build_equal_weight_targets(frame: pd.DataFrame, top_n: int) -> pd.DataFrame:
    # If the eligible universe is smaller than target portfolio size, trigger cash fallback (empty portfolio)
    if len(frame) < top_n:
        return pd.DataFrame(columns=["symbol", "target_weight"])

    # Sort descending by momentum, then ascending by symbol as tie-breaker
    sorted_frame = frame.sort_values(
        by=["momentum_30d_skip_1d", "symbol"], ascending=[False, True]
    ).reset_index(drop=True)

    selected = sorted_frame.iloc[:top_n].copy()
    selected["target_weight"] = 1.0 / top_n

    return selected[["symbol", "target_weight"]]
