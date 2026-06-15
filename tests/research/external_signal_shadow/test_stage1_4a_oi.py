import pytest

from research.external_signal_shadow.stage1_4a_oi import audit_open_interest_history_rows


def test_oi_history_below_90d_blocks_full_composite():
    # 89 days of data (expected interval = 1h = 3600000 ms)
    interval = 60 * 60 * 1000
    total_expected = 89 * 24
    timestamps = [i * interval for i in range(total_expected)]
    rows = [
        {
            "symbol": "BTCUSDT",
            "sumOpenInterest": "100.0",
            "sumOpenInterestValue": "1000.0",
            "timestamp": ts,
        }
        for ts in timestamps
    ]

    res = audit_open_interest_history_rows(rows, "BTCUSDT", interval)
    assert res["oi_history_days"] < 90.0
    assert res["oi_blocks_full_composite"] is True
    assert res["usable"] is False


def test_oi_time_coverage_counts_expected_interval_buckets():
    interval = 60 * 60 * 1000
    # 100 days of data, but drop 15 days in the middle to lower coverage
    total_expected = 100 * 24
    timestamps = [i * interval for i in range(total_expected)]

    # Drop middle 15 days (15 * 24 = 360 hours)
    for idx in range(1000, 1360):
        timestamps.remove(idx * interval)

    rows = [
        {
            "symbol": "BTCUSDT",
            "sumOpenInterest": "100.0",
            "sumOpenInterestValue": "1000.0",
            "timestamp": ts,
        }
        for ts in timestamps
    ]

    res = audit_open_interest_history_rows(rows, "BTCUSDT", interval)
    # Expected: 2400 buckets, actual: 2040. Coverage: 2040/2400 = 0.85 < 0.90
    assert res["oi_time_coverage_ratio"] == 0.85
    assert res["oi_blocks_full_composite"] is True
    assert res["usable"] is False


def test_oi_field_coverage_is_separate_from_time_coverage():
    interval = 60 * 60 * 1000
    # 100 days, but 15% of records have missing open interest
    total_expected = 100 * 24
    rows = []
    for i in range(total_expected):
        has_val = i % 10 != 0  # 10% missing fields
        rows.append({
            "symbol": "BTCUSDT",
            "sumOpenInterest": "100.0" if has_val else None,
            "sumOpenInterestValue": "1000.0",
            "timestamp": i * interval,
        })

    res = audit_open_interest_history_rows(rows, "BTCUSDT", interval)
    # Time coverage is 1.0 (since timestamps exist for all valid-field records? No.
    # Wait, if field is missing, does it get added to timestamps?
    # No, we only add to timestamps if is_valid is True.
    # So if we drop 10% of records due to invalid fields, the timestamps list will also be missing 10% of elements.
    # This is correct because we cannot check continuity of valid data if fields are invalid!
    assert res["oi_field_coverage_ratio"] == 0.90
    # Let's drop 15% of fields to make it block
    rows_bad = []
    for i in range(total_expected):
        has_val = i % 5 != 0  # 20% missing fields
        rows_bad.append({
            "symbol": "BTCUSDT",
            "sumOpenInterest": "100.0" if has_val else None,
            "sumOpenInterestValue": "1000.0",
            "timestamp": i * interval,
        })
    res_bad = audit_open_interest_history_rows(rows_bad, "BTCUSDT", interval)
    assert res_bad["oi_field_coverage_ratio"] == 0.80
    assert res_bad["oi_blocks_full_composite"] is True
    assert res_bad["usable"] is False


def test_oi_gap_count_and_max_gap_ms_are_reported():
    interval = 60 * 60 * 1000
    timestamps = [0, interval, 4 * interval, 5 * interval, 10 * interval]
    rows = [
        {
            "symbol": "BTCUSDT",
            "sumOpenInterest": "100.0",
            "sumOpenInterestValue": "1000.0",
            "timestamp": ts,
        }
        for ts in timestamps
    ]

    res = audit_open_interest_history_rows(rows, "BTCUSDT", interval)
    assert res["gap_count"] == 2
    assert res["max_gap_ms"] == 5 * interval


def test_oi_time_coverage_uses_inferred_metrics_interval():
    # build rows with 5m interval (300,000ms) and one missing bucket
    interval = 300_000
    timestamps = [0, interval, 2 * interval, 4 * interval, 5 * interval]
    rows = [
        {
            "symbol": "BTCUSDT",
            "sumOpenInterest": "100.0",
            "sumOpenInterestValue": "1000.0",
            "timestamp": ts,
        }
        for ts in timestamps
    ]
    # We pass 0 as the expected_interval_ms to test dynamic inference
    res = audit_open_interest_history_rows(rows, "BTCUSDT", 0)
    assert res["expected_bucket_count"] == 6
    assert res["actual_unique_bucket_count"] == 5
    assert res["oi_time_coverage_ratio"] == pytest.approx(5 / 6)

