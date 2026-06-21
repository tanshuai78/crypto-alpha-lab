from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    CANDIDATE_1H,
    CANDIDATE_15M,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_quality import (
    build_source_quality_report,
    candidate_window_supported_by_symbol,
)


def test_15m_candidate_rejected_when_oi_interval_too_sparse():
    # 15m candidate requires median <= 15m and P95 <= 30m
    # Here we simulate hourly updates (3600000 ms)
    oi_stats = {
        "BTCUSDT": {
            "oi_median_interval_ms": 3600000.0,
            "oi_p95_interval_ms": 3600000.0,
        }
    }
    price_stats = {
        "BTCUSDT": {
            "price_median_interval_ms": 900000.0,
            "price_p95_interval_ms": 900000.0,
        }
    }
    supported = candidate_window_supported_by_symbol(CANDIDATE_15M, oi_stats, price_stats)
    assert supported["BTCUSDT"] is False

def test_1h_candidate_supported_when_oi_interval_within_limit():
    oi_stats = {
        "BTCUSDT": {
            "oi_median_interval_ms": 3600000.0,
            "oi_p95_interval_ms": 3600000.0,
        }
    }
    price_stats = {
        "BTCUSDT": {
            "price_median_interval_ms": 3600000.0,
            "price_p95_interval_ms": 3600000.0,
        }
    }
    supported = candidate_window_supported_by_symbol(CANDIDATE_1H, oi_stats, price_stats)
    assert supported["BTCUSDT"] is True

def test_candidate_window_supported_is_symbol_specific():
    # BTC has 15m, ETH has 1h
    oi_stats = {
        "BTCUSDT": {
            "oi_median_interval_ms": 900000.0,
            "oi_p95_interval_ms": 1800000.0,
        },
        "ETHUSDT": {
            "oi_median_interval_ms": 3600000.0,
            "oi_p95_interval_ms": 3600000.0,
        }
    }
    price_stats = {
        "BTCUSDT": {
            "price_median_interval_ms": 900000.0,
            "price_p95_interval_ms": 1800000.0,
        },
        "ETHUSDT": {
            "price_median_interval_ms": 900000.0,
            "price_p95_interval_ms": 1800000.0,
        }
    }
    supported = candidate_window_supported_by_symbol(CANDIDATE_15M, oi_stats, price_stats)
    assert supported["BTCUSDT"] is True
    assert supported["ETHUSDT"] is False

def test_price_interval_gate_rejects_15m_candidate_when_price_bars_are_hourly():
    oi_stats = {
        "BTCUSDT": {
            "oi_median_interval_ms": 900000.0,
            "oi_p95_interval_ms": 1800000.0,
        }
    }
    price_stats = {
        "BTCUSDT": {
            "price_median_interval_ms": 3600000.0,
            "price_p95_interval_ms": 3600000.0,
        }
    }
    supported = candidate_window_supported_by_symbol(CANDIDATE_15M, oi_stats, price_stats)
    assert supported["BTCUSDT"] is False

def test_source_quality_reports_oi_median_and_p95_interval():
    # Simulate some rows to build stats
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": 1600000000000},
        {"symbol": "BTCUSDT", "timestamp_ms": 1600000900000}, # 15 min gap
        {"symbol": "BTCUSDT", "timestamp_ms": 1600001800000}, # 15 min gap
    ]
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": 1600000000000},
        {"symbol": "BTCUSDT", "bar_start_ms": 1600000900000},
        {"symbol": "BTCUSDT", "bar_start_ms": 1600001800000},
    ]
    report = build_source_quality_report(oi_rows, price_rows, ("BTCUSDT",))
    assert report["oi_median_interval_ms"] == 900000.0
    assert report["price_median_interval_ms"] == 900000.0
    assert report["candidate_window_supported_by_symbol"][CANDIDATE_15M]["BTCUSDT"] is True
    assert report["candidate_window_supported_by_symbol"][CANDIDATE_1H]["BTCUSDT"] is True

def test_source_quality_reports_stale_oi_and_price_counts():
    # Staleness test. Suppose config max staleness is 3600000 ms.
    # We provide rows that have a gap of 2 hours.
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": 1600000000000},
        {"symbol": "BTCUSDT", "timestamp_ms": 1600007200000}, # 2h gap
    ]
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": 1600000000000},
        {"symbol": "BTCUSDT", "bar_start_ms": 1600007200000}, # 2h gap
    ]
    report = build_source_quality_report(oi_rows, price_rows, ("BTCUSDT",))
    assert report["stale_oi_bucket_count"] == 1
    assert report["stale_price_bucket_count"] == 1
    assert report["max_oi_staleness_ms_observed"] == 7200000.0
    assert report["max_price_gap_ms_observed"] == 7200000.0
    assert report["oi_data_granularity_minutes"] == 120.0
    assert report["price_data_granularity_minutes"] == 120.0
