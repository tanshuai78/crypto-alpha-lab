from __future__ import annotations

from collections import defaultdict
from typing import Any


def _as_float(val: Any) -> float:
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def _as_int(val: Any) -> int:
    try:
        return int(val) if val is not None else 0
    except (ValueError, TypeError):
        return 0


def compute_overlap_reports(
    liq_windows: list[dict[str, Any]],
    funding_rows: list[dict[str, Any]] | None,
    oi_rows: list[dict[str, Any]] | None,
    price_rows: list[Any] | None,
    funding_publish_lag_ms: int,
    max_oi_staleness_ms: int,
    min_abs_funding_rate_preview: float,
    min_abs_oi_change_ratio_preview: float,
    min_abs_price_return_1h_preview: float,
) -> dict[str, Any]:
    policy_report = {
        "funding": "asof_latest_before_bucket_end_minus_lag",
        "oi": "asof_latest_before_bucket_end_with_staleness_limit",
        "price": "bucket_exact_or_covering"
    }

    if not funding_rows or not oi_rows or not price_rows:
        return {
            "alignment_overlap_available": False,
            "data_alignment_overlap_window_count_15m": 0,
            "stress_condition_overlap_window_count_15m": 0,
            "data_alignment_overlap_event_days": 0,
            "stress_condition_overlap_event_days": 0,
            "symbols_with_alignment_overlap": 0,
            "alignment_policy": policy_report,
        }

    # 1. Normalize and group funding
    funding_by_symbol = defaultdict(list)
    for r in funding_rows:
        sym = r.get("symbol")
        if not sym:
            continue
        fundingTime = _as_int(r.get("fundingTime"))
        fundingRate = _as_float(r.get("fundingRate"))
        funding_by_symbol[sym].append({
            "fundingTime": fundingTime,
            "fundingRate": fundingRate,
        })
    for sym in funding_by_symbol:
        funding_by_symbol[sym].sort(key=lambda x: x["fundingTime"])

    # 2. Normalize and group OI
    oi_by_symbol = defaultdict(list)
    for r in oi_rows:
        sym = r.get("symbol")
        if not sym:
            continue
        ts = _as_int(r.get("timestamp"))
        oi_val = _as_float(r.get("sumOpenInterest"))
        oi_by_symbol[sym].append({
            "timestamp": ts,
            "sumOpenInterest": oi_val,
        })
    # Compute oi_change_ratio
    for sym in oi_by_symbol:
        oi_by_symbol[sym].sort(key=lambda x: x["timestamp"])
        rows = oi_by_symbol[sym]
        for i in range(len(rows)):
            if i > 0 and rows[i - 1]["sumOpenInterest"] > 0:
                change = (rows[i]["sumOpenInterest"] - rows[i - 1]["sumOpenInterest"]) / rows[i - 1]["sumOpenInterest"]
            else:
                change = 0.0
            # Also allow pre-calculated oi_change_ratio if present in original data
            # But we default to calculated one.
            rows[i]["oi_change_ratio"] = change

    # 3. Normalize and group price
    price_by_symbol = defaultdict(list)
    for r in price_rows:
        if isinstance(r, dict):
            sym = r.get("symbol")
            open_time = r.get("open_time") or r.get("timestamp") or r.get("bar_start_ms") or r.get("t")
            open_p = r.get("open") or r.get("open_price") or r.get("o")
            close_p = r.get("close") or r.get("close_price") or r.get("c")
            abs_ret_pre = r.get("abs_return_1h") or r.get("return_1h")
        elif isinstance(r, (list, tuple)) and len(r) >= 5:
            sym = None # caller filters or we assume same symbol
            open_time = r[0]
            open_p = r[1]
            close_p = r[4]
            abs_ret_pre = None
        else:
            continue

        open_time_val = _as_int(open_time)
        open_price_val = _as_float(open_p)
        close_price_val = _as_float(close_p)

        price_by_symbol[sym or "DEFAULT"].append({
            "open_time": open_time_val,
            "open_price": open_price_val,
            "close_price": close_price_val,
            "abs_return_1h_pre": abs_ret_pre,
        })

    for sym in price_by_symbol:
        price_by_symbol[sym].sort(key=lambda x: x["open_time"])
        rows = price_by_symbol[sym]
        for i in range(len(rows)):
            if rows[i]["abs_return_1h_pre"] is not None:
                rows[i]["abs_return_1h"] = abs(float(rows[i]["abs_return_1h_pre"]))
                continue

            # Lookback 1 hour (3600000 ms)
            best_j = -1
            best_diff = 999999999
            for j in range(i):
                diff = abs((rows[i]["open_time"] - rows[j]["open_time"]) - 3600000)
                # Lookback range: 45m to 75m
                if 2700000 <= (rows[i]["open_time"] - rows[j]["open_time"]) <= 4500000:
                    if diff < best_diff:
                        best_diff = diff
                        best_j = j
            if best_j != -1 and rows[best_j]["open_price"] > 0:
                ret = abs(rows[i]["close_price"] - rows[best_j]["open_price"]) / rows[best_j]["open_price"]
            else:
                if rows[i]["open_price"] > 0:
                    ret = abs(rows[i]["close_price"] - rows[i]["open_price"]) / rows[i]["open_price"]
                else:
                    ret = 0.0
            rows[i]["abs_return_1h"] = ret

    # Process windows
    alignment_count = 0
    stress_count = 0
    symbols_aligned = set()
    alignment_days = set()
    stress_days = set()

    for w in liq_windows:
        sym = w["symbol"]
        bucket_start_ms = int(w["bucket_start_ms"])
        bucket_end_ms = int(w["bucket_end_ms"])
        day_key = w["day_key"]

        # 1. As-of funding
        f_list = funding_by_symbol.get(sym, [])
        target_f = None
        # Latest funding rate row F where F.fundingTime <= bucket_end_ms - funding_publish_lag_ms
        for f in reversed(f_list):
            if f["fundingTime"] <= bucket_end_ms - funding_publish_lag_ms:
                target_f = f
                break

        if not target_f:
            continue

        # 2. As-of OI
        oi_list = oi_by_symbol.get(sym, [])
        target_o = None
        # Latest OI row O where O.timestamp <= bucket_end_ms and bucket_end_ms - O.timestamp <= max_oi_staleness_ms
        for o in reversed(oi_list):
            if o["timestamp"] <= bucket_end_ms:
                if bucket_end_ms - o["timestamp"] <= max_oi_staleness_ms:
                    target_o = o
                break

        if not target_o:
            continue

        # 3. Aligned price
        p_list = price_by_symbol.get(sym, price_by_symbol.get("DEFAULT", []))
        target_p = None
        # P.open_time is closest to bucket_start_ms within 15 mins
        best_diff = 15 * 60 * 1000
        for p in p_list:
            diff = abs(p["open_time"] - bucket_start_ms)
            if diff <= best_diff:
                best_diff = diff
                target_p = p

        if not target_p:
            continue

        # Data alignment matched!
        alignment_count += 1
        symbols_aligned.add(sym)
        alignment_days.add(day_key)

        # Check preview conditions
        f_rate = abs(target_f["fundingRate"])
        oi_chg = abs(target_o["oi_change_ratio"])
        p_ret = target_p["abs_return_1h"]

        if (
            f_rate >= min_abs_funding_rate_preview
            and oi_chg >= min_abs_oi_change_ratio_preview
            and p_ret >= min_abs_price_return_1h_preview
        ):
            stress_count += 1
            stress_days.add(day_key)

    return {
        "alignment_overlap_available": True,
        "data_alignment_overlap_window_count_15m": alignment_count,
        "stress_condition_overlap_window_count_15m": stress_count,
        "data_alignment_overlap_event_days": len(alignment_days),
        "stress_condition_overlap_event_days": len(stress_days),
        "symbols_with_alignment_overlap": len(symbols_aligned),
        "alignment_policy": policy_report,
    }
