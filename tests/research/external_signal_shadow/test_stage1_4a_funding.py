"""
tests/research/external_signal_shadow/test_stage1_4a_funding.py
"""

from research.external_signal_shadow.stage1_4a_funding import (
    audit_funding_history_rows,
    funding_state_at_event,
)


def test_funding_settlement_coverage_detects_missing_8h_records():
    # 8h = 28800000 ms
    interval = 8 * 60 * 60 * 1000

    # 180 days of funding rate settlements at 8h interval
    # 180 days * 3 settlements/day = 540 settlements
    total_expected = 540
    timestamps = [i * interval for i in range(total_expected)]

    # Intentionally drop 10 settlements to test coverage detection
    # This leaves 530 unique settlements
    for idx_to_drop in [10, 20, 30, 40, 50, 100, 200, 300, 400, 500]:
        timestamps.remove(idx_to_drop * interval)

    rows = [
        {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingTime": ts}
        for ts in timestamps
    ]

    res = audit_funding_history_rows(rows, "BTCUSDT")

    assert res["funding_record_count"] == 530
    assert res["funding_settlement_coverage_ratio"] < 1.0
    assert res["missing_settlement_count"] == 10
    # 180 days is well above 90 days, but let's check exact usability:
    # 530 / 540 = 0.981 > 0.95, so it should be usable
    assert res["usable"] is True

    # Now let's drop enough to make it unusable (< 0.95 coverage)
    # 540 * 0.90 = 486
    bad_timestamps = [i * interval for i in range(540)]
    for idx in range(100, 200):
        bad_timestamps.remove(idx * interval)
    bad_rows = [
        {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingTime": ts}
        for ts in bad_timestamps
    ]
    res_bad = audit_funding_history_rows(bad_rows, "BTCUSDT")
    assert res_bad["funding_settlement_coverage_ratio"] < 0.95
    assert res_bad["usable"] is False


def test_funding_field_coverage_counts_valid_rates_only():
    interval = 8 * 60 * 60 * 1000
    rows = [
        {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingTime": 0},
        {"symbol": "BTCUSDT", "fundingRate": None, "fundingTime": interval}, # null rate
        {"symbol": "BTCUSDT", "fundingRate": "0.0002", "fundingTime": 2 * interval},
    ]
    res = audit_funding_history_rows(rows, "BTCUSDT")
    assert res["funding_record_count"] == 3
    # 2 out of 3 are valid
    assert res["funding_field_coverage_ratio"] == 2.0 / 3.0
    assert res["usable"] is False  # below 0.95 field coverage and below 90 days


def test_funding_asof_policy_uses_latest_record_before_available_minus_lag():
    rows = [
        {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingTime": 1000},
        {"symbol": "BTCUSDT", "fundingRate": "0.0002", "fundingTime": 2000},
        {"symbol": "BTCUSDT", "fundingRate": "0.0003", "fundingTime": 3000},
    ]
    lag = 100
    # If event is at 3100, then event_available_at - lag = 3000.
    # Record at 3000 has availability 3100, which matches event_available_at.
    # So we should get 3000.
    res = funding_state_at_event(rows, 3100, lag)
    assert res is not None
    assert res["fundingRate"] == "0.0003"

    # If event is at 3050, event_available_at - lag = 2950.
    # Eligible records are <= 2950, so max eligible is 2000.
    res2 = funding_state_at_event(rows, 3050, lag)
    assert res2 is not None
    assert res2["fundingRate"] == "0.0002"


def test_funding_asof_policy_does_not_use_future_record():
    rows = [
        {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingTime": 1000},
        {"symbol": "BTCUSDT", "fundingRate": "0.0002", "fundingTime": 2000},
    ]
    lag = 100
    # Event at 1050 -> event_available - lag = 950.
    # No record <= 950, so should return None.
    res = funding_state_at_event(rows, 1050, lag)
    assert res is None
