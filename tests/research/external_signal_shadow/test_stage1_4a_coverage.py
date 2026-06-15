"""
tests/research/external_signal_shadow/test_stage1_4a_coverage.py
"""

from research.external_signal_shadow.stage1_4a_coverage import compute_time_coverage


def test_coverage_consecutive_1h():
    # 4 consecutive 1h buckets (expected interval = 1 hour = 3600000 ms)
    interval = 60 * 60 * 1000
    timestamps = [0, interval, 2 * interval, 3 * interval]
    res = compute_time_coverage(timestamps, interval)

    assert res["expected_bucket_count"] == 4
    assert res["actual_unique_bucket_count"] == 4
    assert res["time_coverage_ratio"] == 1.0
    assert res["gap_count"] == 0
    assert res["max_gap_ms"] == 0
    assert res["history_days"] == (3 * interval) / (24 * 60 * 60 * 1000)


def test_coverage_missing_1h():
    # 4 buckets but missing the second one
    interval = 60 * 60 * 1000
    timestamps = [0, 2 * interval, 3 * interval]
    res = compute_time_coverage(timestamps, interval)

    assert res["expected_bucket_count"] == 4
    assert res["actual_unique_bucket_count"] == 3
    assert res["time_coverage_ratio"] == 0.75
    assert res["gap_count"] == 1
    assert res["max_gap_ms"] == 2 * interval


def test_coverage_duplicate_timestamps():
    interval = 60 * 60 * 1000
    timestamps = [0, 0, interval, interval, 2 * interval]
    res = compute_time_coverage(timestamps, interval)

    assert res["expected_bucket_count"] == 3
    assert res["actual_unique_bucket_count"] == 3
    assert res["time_coverage_ratio"] == 1.0


def test_coverage_empty_or_invalid():
    res_empty = compute_time_coverage([], 3600000)
    assert res_empty["time_coverage_ratio"] == 0.0
    assert res_empty["gap_count"] == 0

    res_zero_interval = compute_time_coverage([1000, 2000], 0)
    assert res_zero_interval["time_coverage_ratio"] == 0.0
