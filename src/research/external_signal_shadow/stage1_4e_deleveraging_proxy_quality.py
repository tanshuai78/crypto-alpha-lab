from collections import defaultdict

from configs import base
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    CANDIDATE_1H,
    CANDIDATE_15M,
)


def _percentile(sorted_data: list[float], pct: float) -> float:
    if not sorted_data:
        return 0.0
    idx = min(len(sorted_data) - 1, max(0, int(len(sorted_data) * pct / 100.0)))
    return float(sorted_data[idx])

def _median(sorted_data: list[float]) -> float:
    return _percentile(sorted_data, 50.0)

def build_oi_interval_stats(oi_rows_by_symbol: dict[str, list[dict]]) -> dict:
    stats = {}
    for symbol, rows in oi_rows_by_symbol.items():
        sorted_rows = sorted(rows, key=lambda x: x["timestamp_ms"])
        gaps = []
        for i in range(1, len(sorted_rows)):
            gap = sorted_rows[i]["timestamp_ms"] - sorted_rows[i-1]["timestamp_ms"]
            gaps.append(gap)

        if gaps:
            gaps.sort()
            stats[symbol] = {
                "oi_median_interval_ms": _median(gaps),
                "oi_p95_interval_ms": _percentile(gaps, 95.0)
            }
        else:
            stats[symbol] = {
                "oi_median_interval_ms": float("inf"),
                "oi_p95_interval_ms": float("inf")
            }
    return stats

def build_price_interval_stats(price_rows_by_symbol: dict[str, list[dict]]) -> dict:
    stats = {}
    for symbol, rows in price_rows_by_symbol.items():
        sorted_rows = sorted(rows, key=lambda x: x["bar_start_ms"])
        gaps = []
        for i in range(1, len(sorted_rows)):
            gap = sorted_rows[i]["bar_start_ms"] - sorted_rows[i-1]["bar_start_ms"]
            gaps.append(gap)

        if gaps:
            gaps.sort()
            stats[symbol] = {
                "price_median_interval_ms": _median(gaps),
                "price_p95_interval_ms": _percentile(gaps, 95.0)
            }
        else:
            stats[symbol] = {
                "price_median_interval_ms": float("inf"),
                "price_p95_interval_ms": float("inf")
            }
    return stats

def candidate_window_supported_by_symbol(
    candidate_name: str,
    oi_interval_stats: dict,
    price_interval_stats: dict
) -> dict:
    supported = {}
    symbols = set(oi_interval_stats.keys()) | set(price_interval_stats.keys())

    for s in symbols:
        oi_stat = oi_interval_stats.get(s, {"oi_median_interval_ms": float("inf"), "oi_p95_interval_ms": float("inf")})
        price_stat = price_interval_stats.get(s, {"price_median_interval_ms": float("inf"), "price_p95_interval_ms": float("inf")})

        med_oi = oi_stat["oi_median_interval_ms"]
        p95_oi = oi_stat["oi_p95_interval_ms"]
        med_pr = price_stat["price_median_interval_ms"]
        p95_pr = price_stat["price_p95_interval_ms"]

        if candidate_name == CANDIDATE_15M:
            max_oi_med = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_MAX_OI_MEDIAN_INTERVAL_MS
            max_oi_p95 = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_MAX_OI_P95_INTERVAL_MS
            max_pr_med = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_MAX_PRICE_MEDIAN_INTERVAL_MS
            max_pr_p95 = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_MAX_PRICE_P95_INTERVAL_MS
        elif candidate_name == CANDIDATE_1H:
            max_oi_med = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_MAX_OI_MEDIAN_INTERVAL_MS
            max_oi_p95 = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_MAX_OI_P95_INTERVAL_MS
            max_pr_med = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_MAX_PRICE_MEDIAN_INTERVAL_MS
            max_pr_p95 = base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_MAX_PRICE_P95_INTERVAL_MS
        else:
            supported[s] = False
            continue

        oi_ok = (med_oi <= max_oi_med) and (p95_oi <= max_oi_p95)
        pr_ok = (med_pr <= max_pr_med) and (p95_pr <= max_pr_p95)
        supported[s] = bool(oi_ok and pr_ok)

    return supported

def build_source_quality_report(
    oi_rows: list[dict],
    price_rows: list[dict],
    expected_symbols: tuple[str, ...]
) -> dict:
    oi_by_symbol = defaultdict(list)
    for r in oi_rows:
        oi_by_symbol[r["symbol"]].append(r)

    price_by_symbol = defaultdict(list)
    for r in price_rows:
        price_by_symbol[r["symbol"]].append(r)

    # Build stats
    oi_stats = build_oi_interval_stats(oi_by_symbol)
    price_stats = build_price_interval_stats(price_by_symbol)

    # Candidate window supported per symbol
    supported_15m = candidate_window_supported_by_symbol(CANDIDATE_15M, oi_stats, price_stats)
    supported_1h = candidate_window_supported_by_symbol(CANDIDATE_1H, oi_stats, price_stats)

    # Overall support is true if at least one expected symbol is supported
    supported_15m_overall = any(supported_15m.get(s, False) for s in expected_symbols)
    supported_1h_overall = any(supported_1h.get(s, False) for s in expected_symbols)

    unsupported_symbols_15m = [s for s in expected_symbols if not supported_15m.get(s, False)]
    unsupported_symbols_1h = [s for s in expected_symbols if not supported_1h.get(s, False)]

    # Staleness & gaps detection
    stale_oi_count = 0
    max_oi_staleness = 0.0
    all_oi_gaps = []

    for symbol, rows in oi_by_symbol.items():
        sorted_rows = sorted(rows, key=lambda x: x["timestamp_ms"])
        for i in range(1, len(sorted_rows)):
            gap = sorted_rows[i]["timestamp_ms"] - sorted_rows[i-1]["timestamp_ms"]
            all_oi_gaps.append(gap)
            if gap > base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MAX_OI_STALENESS_MS:
                stale_oi_count += 1
            if gap > max_oi_staleness:
                max_oi_staleness = float(gap)

    stale_price_count = 0
    max_price_gap = 0.0
    all_price_gaps = []

    for symbol, rows in price_by_symbol.items():
        sorted_rows = sorted(rows, key=lambda x: x["bar_start_ms"])
        for i in range(1, len(sorted_rows)):
            gap = sorted_rows[i]["bar_start_ms"] - sorted_rows[i-1]["bar_start_ms"]
            all_price_gaps.append(gap)
            if gap > base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MAX_PRICE_STALENESS_MS:
                stale_price_count += 1
            if gap > max_price_gap:
                max_price_gap = float(gap)

    # Average/median data granularity in minutes
    oi_gaps_sorted = sorted(all_oi_gaps)
    price_gaps_sorted = sorted(all_price_gaps)

    oi_median_ms = _median(oi_gaps_sorted) if oi_gaps_sorted else 0.0
    price_median_ms = _median(price_gaps_sorted) if price_gaps_sorted else 0.0

    oi_gran_min = oi_median_ms / (60.0 * 1000.0)
    price_gran_min = price_median_ms / (60.0 * 1000.0)

    # History duration in days
    min_oi_ts = min((r["timestamp_ms"] for r in oi_rows), default=0)
    max_oi_ts = max((r["timestamp_ms"] for r in oi_rows), default=0)
    min_pr_ts = min((r["bar_start_ms"] for r in price_rows), default=0)
    max_pr_ts = max((r["bar_start_ms"] for r in price_rows), default=0)

    oi_history_days = (max_oi_ts - min_oi_ts) / (24.0 * 3600.0 * 1000.0) if max_oi_ts > min_oi_ts else 0.0
    price_history_days = (max_pr_ts - min_pr_ts) / (24.0 * 3600.0 * 1000.0) if max_pr_ts > min_pr_ts else 0.0

    # Data source quality warnings
    oi_source_quality = "exchange_reported_hourly_snapshot"
    if oi_gran_min > 16.0:
        oi_source_quality = "hourly_oi_granularity_mismatch_warning"

    return {
        "oi_median_interval_ms": oi_median_ms,
        "oi_p95_interval_ms": _percentile(oi_gaps_sorted, 95.0) if oi_gaps_sorted else 0.0,
        "price_median_interval_ms": price_median_ms,
        "price_p95_interval_ms": _percentile(price_gaps_sorted, 95.0) if price_gaps_sorted else 0.0,

        "candidate_window_supported_by_symbol": {
            CANDIDATE_15M: supported_15m,
            CANDIDATE_1H: supported_1h
        },
        "candidate_window_supported_overall": {
            CANDIDATE_15M: supported_15m_overall,
            CANDIDATE_1H: supported_1h_overall
        },
        "unsupported_symbols": {
            CANDIDATE_15M: unsupported_symbols_15m,
            CANDIDATE_1H: unsupported_symbols_1h
        },

        "stale_oi_bucket_count": stale_oi_count,
        "stale_price_bucket_count": stale_price_count,
        "max_oi_staleness_ms_observed": max_oi_staleness,
        "max_price_gap_ms_observed": max_price_gap,

        "oi_data_granularity_minutes": oi_gran_min,
        "price_data_granularity_minutes": price_gran_min,
        "oi_history_days": oi_history_days,
        "price_history_days": price_history_days,
        "oi_source_quality": oi_source_quality,
        "price_source_quality": "close_price_proxy_not_fill_price"
    }
