"""
src/research/external_signal_shadow/stage1_4a_price.py
"""

from configs.base import EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_PRICE_INTERVAL_MS
from research.external_signal_shadow.stage1_4a_coverage import compute_time_coverage


def audit_price_source_rows(
    rows: list, expected_symbol: str, source_kind: str
) -> dict:
    """
    Audits price source rows (either futures klines or spot proxy klines).
    Calculates actual history_days, bar coverage ratio, and time coverage.
    """
    symbol_rows = []
    for r in rows:
        if isinstance(r, dict):
            # If symbol key is present, filter by it. Otherwise assume matching.
            if "symbol" in r and r["symbol"] != expected_symbol:
                continue
            symbol_rows.append(r)
        elif isinstance(r, list | tuple):
            # Raw lists are assumed to be for the expected symbol
            symbol_rows.append(r)

    record_count = len(symbol_rows)

    if record_count == 0:
        proxy_used = (source_kind == "spot_klines_proxy")
        return {
            "price_source_preference": "futures_klines_preferred",
            "price_source": source_kind,
            "price_venue_proxy_used": proxy_used,
            "price_history_days": 0.0,
            "price_bar_count": 0,
            "price_bar_coverage_ratio": 0.0,
            "time_coverage_ratio": 0.0,
            "gap_count": 0,
            "max_gap_ms": 0,
        }

    valid_field_count = 0
    timestamps = []

    for r in symbol_rows:
        open_time = None
        close_price = None

        if isinstance(r, dict):
            open_time = None
            for k in ("open_time", "timestamp", "bar_start_ms", "t"):
                if r.get(k) is not None:
                    open_time = r[k]
                    break

            close_price = None
            for k in ("close", "close_price", "c"):
                if r.get(k) is not None:
                    close_price = r[k]
                    break
        elif isinstance(r, list | tuple) and len(r) >= 5:
            open_time = r[0]
            close_price = r[4]

        if open_time is not None and close_price is not None:
            valid_field_count += 1
            timestamps.append(int(open_time))

    price_bar_coverage_ratio = float(valid_field_count / record_count) if record_count > 0 else 0.0

    coverage = compute_time_coverage(
        timestamps, EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_PRICE_INTERVAL_MS
    )

    proxy_used = (source_kind == "spot_klines_proxy")

    return {
        "price_source_preference": "futures_klines_preferred",
        "price_source": source_kind,
        "price_venue_proxy_used": proxy_used,
        "price_history_days": coverage["history_days"],
        "price_bar_count": record_count,
        "price_bar_coverage_ratio": price_bar_coverage_ratio,
        "time_coverage_ratio": coverage["time_coverage_ratio"],
        "gap_count": coverage["gap_count"],
        "max_gap_ms": coverage["max_gap_ms"],
    }
