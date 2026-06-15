"""
src/research/external_signal_shadow/stage1_4a_oi.py
"""

from configs.base import (
    EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN,
    EXTERNAL_SIGNAL_STAGE1_4_OI_FIELD_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_OI_TIME_COVERAGE_MIN_RATIO,
)
from research.external_signal_shadow.stage1_4a_coverage import compute_time_coverage


def audit_open_interest_history_rows(
    rows: list[dict], expected_symbol: str, expected_interval_ms: int
) -> dict:
    """
    Audits Open Interest history rows for the expected symbol.
    """
    symbol_rows = [r for r in rows if r.get("symbol") == expected_symbol]
    record_count = len(symbol_rows)

    if record_count == 0:
        return {
            "oi_source": "binance_openInterestHist_or_local_archive",
            "oi_record_count": 0,
            "oi_history_days": 0.0,
            "oi_field_coverage_ratio": 0.0,
            "oi_time_coverage_ratio": 0.0,
            "expected_bucket_count": 0,
            "actual_unique_bucket_count": 0,
            "gap_count": 0,
            "max_gap_ms": 0,
            "oi_history_limit_detected_days": 0.0,
            "oi_blocks_full_composite": True,
            "source_quality": "missing",
            "usable": False,
        }

    # Field coverage: fields must be symbol, sumOpenInterest, sumOpenInterestValue, timestamp
    valid_field_count = 0
    timestamps = []
    has_local_archive = False

    for r in symbol_rows:
        is_valid = (
            r.get("symbol") == expected_symbol
            and r.get("sumOpenInterest") is not None
            and r.get("sumOpenInterestValue") is not None
            and r.get("timestamp") is not None
        )
        if is_valid:
            valid_field_count += 1
            timestamps.append(int(r["timestamp"]))

        # Check if rows are marked as local archive
        if r.get("source") == "local_archive" or r.get("source_quality") == "local_archive":
            has_local_archive = True

    field_coverage_ratio = float(valid_field_count / record_count) if record_count > 0 else 0.0

    # Determine expected interval
    interval_ms = expected_interval_ms
    # Try to dynamically infer interval if we have enough timestamps
    inferred_int = 0
    if len(timestamps) >= 2:
        sorted_ts = sorted(list(set(timestamps)))
        deltas = [sorted_ts[i] - sorted_ts[i-1] for i in range(1, len(sorted_ts))]
        positive_deltas = [d for d in deltas if d > 0]
        if positive_deltas:
            positive_deltas.sort()
            n = len(positive_deltas)
            if n % 2 == 1:
                inferred_int = positive_deltas[n // 2]
            else:
                inferred_int = (positive_deltas[n // 2 - 1] + positive_deltas[n // 2]) // 2

    # Prefer inferred interval if available
    if inferred_int > 0:
        interval_ms = inferred_int

    # If interval_ms <= 0, we cannot compute coverage
    if interval_ms <= 0:
        return {
            "oi_source": "binance_openInterestHist_or_local_archive",
            "oi_record_count": record_count,
            "oi_history_days": 0.0,
            "oi_field_coverage_ratio": field_coverage_ratio,
            "oi_time_coverage_ratio": 0.0,
            "expected_bucket_count": 0,
            "actual_unique_bucket_count": 0,
            "gap_count": 0,
            "max_gap_ms": 0,
            "oi_history_limit_detected_days": 0.0,
            "oi_blocks_full_composite": True,
            "source_quality": "local_archive" if has_local_archive else "public_history",
            "usable": False,
            "primary_blocker": "oi_interval_unavailable",
        }

    # Compute time coverage
    coverage = compute_time_coverage(timestamps, interval_ms)

    oi_history_days = coverage["history_days"]
    oi_time_coverage_ratio = coverage["time_coverage_ratio"]

    # Hard rules to block full composite
    oi_blocks_full_composite = (
        oi_history_days < EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN
        or oi_time_coverage_ratio < EXTERNAL_SIGNAL_STAGE1_4_OI_TIME_COVERAGE_MIN_RATIO
        or field_coverage_ratio < EXTERNAL_SIGNAL_STAGE1_4_OI_FIELD_COVERAGE_MIN_RATIO
    )

    source_quality = "local_archive" if has_local_archive else "public_history"
    usable = not oi_blocks_full_composite

    return {
        "oi_source": "binance_openInterestHist_or_local_archive",
        "oi_record_count": record_count,
        "oi_history_days": oi_history_days,
        "oi_field_coverage_ratio": field_coverage_ratio,
        "oi_time_coverage_ratio": oi_time_coverage_ratio,
        "expected_bucket_count": coverage["expected_bucket_count"],
        "actual_unique_bucket_count": coverage["actual_unique_bucket_count"],
        "gap_count": coverage["gap_count"],
        "max_gap_ms": coverage["max_gap_ms"],
        "oi_history_limit_detected_days": oi_history_days,
        "oi_blocks_full_composite": oi_blocks_full_composite,
        "source_quality": source_quality,
        "usable": usable,
    }

