from research.external_signal_shadow.stage1_4a_lq30_overlap import compute_overlap_reports


def test_overlap_uses_funding_asof_not_exact_bucket_match():
    # 15m bucket: 900,000 to 1,800,000.
    # bucket_end_ms = 1,800,000.
    # lag = 300,000 ms.
    # We look for fundingTime <= 1,800,000 - 300,000 = 1,500,000.
    # Row with fundingTime = 0 is eligible.
    liq_windows = [{"symbol": "BTCUSDT", "bucket_start_ms": 900000, "bucket_end_ms": 1800000, "day_key": "2026-06-01"}]
    funding_rows = [{"symbol": "BTCUSDT", "fundingTime": 0, "fundingRate": "0.0005"}]

    # OI: timestamp <= 1,800,000, difference <= 3,600,000.
    # Row with timestamp = 1,500,000 is eligible.
    # We have two rows to compute oi_change_ratio:
    # row 1: ts=0, sumOpenInterest=100
    # row 2: ts=1,500,000, sumOpenInterest=98 -> ratio = -0.02
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp": 0, "sumOpenInterest": "100", "sumOpenInterestValue": "1000"},
        {"symbol": "BTCUSDT", "timestamp": 1500000, "sumOpenInterest": "98", "sumOpenInterestValue": "980"}
    ]

    # Price: bar_start_ms == 900,000.
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": 0, "open_price": 64000, "close_price": 65000},
        {"symbol": "BTCUSDT", "bar_start_ms": 900000, "open_price": 65000, "close_price": 65975} # return = 0.015
    ]

    report = compute_overlap_reports(
        liq_windows,
        funding_rows,
        oi_rows,
        price_rows,
        funding_publish_lag_ms=300000,
        max_oi_staleness_ms=3600000,
        min_abs_funding_rate_preview=0.0001,
        min_abs_oi_change_ratio_preview=0.01,
        min_abs_price_return_1h_preview=0.01,
    )

    assert report["alignment_overlap_available"] is True
    assert report["data_alignment_overlap_window_count_15m"] == 1
    assert report["stress_condition_overlap_window_count_15m"] == 1
    assert report["symbols_with_alignment_overlap"] == 1
    assert report["data_alignment_overlap_event_days"] == 1


def test_overlap_stress_condition_filtering():
    liq_windows = [{"symbol": "BTCUSDT", "bucket_start_ms": 900000, "bucket_end_ms": 1800000, "day_key": "2026-06-01"}]
    funding_rows = [{"symbol": "BTCUSDT", "fundingTime": 0, "fundingRate": "0.0000"}]  # funding rate 0.0
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp": 0, "sumOpenInterest": "100"},
        {"symbol": "BTCUSDT", "timestamp": 1500000, "sumOpenInterest": "100"}  # change ratio 0.0
    ]
    price_rows = [{"symbol": "BTCUSDT", "bar_start_ms": 900000, "open_price": 65000, "close_price": 65000}]  # return 0.0

    report = compute_overlap_reports(
        liq_windows,
        funding_rows,
        oi_rows,
        price_rows,
        funding_publish_lag_ms=300000,
        max_oi_staleness_ms=3600000,
        min_abs_funding_rate_preview=0.0001,  # requires > 0.0001
        min_abs_oi_change_ratio_preview=0.01,
        min_abs_price_return_1h_preview=0.01,
    )

    assert report["alignment_overlap_available"] is True
    assert report["data_alignment_overlap_window_count_15m"] == 1
    # stress overlap should be 0 because preview conditions are not met
    assert report["stress_condition_overlap_window_count_15m"] == 0


def test_overlap_price_covering_bar_at_exact_15m_boundary_counts_as_aligned():
    liq_windows = [{"symbol": "BTCUSDT", "bucket_start_ms": 900000, "bucket_end_ms": 1800000, "day_key": "2026-06-01"}]
    funding_rows = [{"symbol": "BTCUSDT", "fundingTime": 0, "fundingRate": "0.0005"}]
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp": 0, "sumOpenInterest": "100", "sumOpenInterestValue": "1000"},
        {"symbol": "BTCUSDT", "timestamp": 1500000, "sumOpenInterest": "98", "sumOpenInterestValue": "980"},
    ]
    # Only a covering bar exactly 15m before the bucket start.
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": 0, "open_price": 64000, "close_price": 65000},
    ]

    report = compute_overlap_reports(
        liq_windows,
        funding_rows,
        oi_rows,
        price_rows,
        funding_publish_lag_ms=300000,
        max_oi_staleness_ms=3600000,
        min_abs_funding_rate_preview=0.0,
        min_abs_oi_change_ratio_preview=0.0,
        min_abs_price_return_1h_preview=0.0,
    )

    assert report["alignment_overlap_available"] is True
    assert report["data_alignment_overlap_window_count_15m"] == 1


def test_runner_without_alignment_inputs_marks_alignment_unavailable():
    report = compute_overlap_reports([], None, None, None, 300000, 3600000, 0.0, 0.0, 0.0)
    assert report["alignment_overlap_available"] is False
