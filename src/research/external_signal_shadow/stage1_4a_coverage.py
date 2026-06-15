"""
src/research/external_signal_shadow/stage1_4a_coverage.py
"""


def compute_time_coverage(timestamps_ms: list[int], expected_interval_ms: int) -> dict:
    """
    Computes time coverage metrics from a list of timestamps and an expected interval.

    Rules:
    - Deduplicates timestamps.
    - If empty list or expected_interval_ms <= 0, returns zeroed dict safely.
    - Expected bucket count = (max_ts - min_ts) // expected_interval_ms + 1.
    - Gaps are consecutive differences greater than expected_interval_ms.
    """
    default_res = {
        "history_days": 0.0,
        "expected_bucket_count": 0,
        "actual_unique_bucket_count": 0,
        "time_coverage_ratio": 0.0,
        "gap_count": 0,
        "max_gap_ms": 0,
    }

    if not timestamps_ms or expected_interval_ms <= 0:
        return default_res

    unique_ts = sorted(list(set(timestamps_ms)))
    min_ts = unique_ts[0]
    max_ts = unique_ts[-1]

    history_days = float((max_ts - min_ts) / (24 * 60 * 60 * 1000))
    expected_bucket_count = int((max_ts - min_ts) // expected_interval_ms) + 1
    actual_unique_bucket_count = len(unique_ts)

    # Note: in case of float/imprecise intervals, use a small epsilon or integer division
    # Since we use millisecond timestamps (integers), integer division is clean.
    time_coverage_ratio = float(actual_unique_bucket_count / expected_bucket_count) if expected_bucket_count > 0 else 0.0

    gap_count = 0
    max_gap_ms = 0
    for i in range(1, len(unique_ts)):
        diff = unique_ts[i] - unique_ts[i - 1]
        if diff > expected_interval_ms:
            gap_count += 1
            if diff > max_gap_ms:
                max_gap_ms = diff

    return {
        "history_days": history_days,
        "expected_bucket_count": expected_bucket_count,
        "actual_unique_bucket_count": actual_unique_bucket_count,
        "time_coverage_ratio": time_coverage_ratio,
        "gap_count": gap_count,
        "max_gap_ms": max_gap_ms,
    }
