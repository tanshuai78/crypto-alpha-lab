from research.external_signal_shadow.stage1_4a_lq30_aggregation import (
    aggregate_forceorder_windows,
    build_density_report,
    build_imbalance_distribution,
    compute_concentration_stats,
)


def test_aggregate_forceorder_windows():
    rows = [
        # BTCUSDT bucket start 900,000 (15m UTC)
        {"symbol": "BTCUSDT", "liquidation_side": "long_liquidation", "notional_usd": 1000.0, "timestamp_ms": 900000},
        {"symbol": "BTCUSDT", "liquidation_side": "long_liquidation", "notional_usd": 500.0, "timestamp_ms": 950000},
        {"symbol": "BTCUSDT", "liquidation_side": "short_liquidation", "notional_usd": 300.0, "timestamp_ms": 1000000},
        # BTCUSDT next bucket start 1,800,000
        {"symbol": "BTCUSDT", "liquidation_side": "short_liquidation", "notional_usd": 2000.0, "timestamp_ms": 1900000},
        # ETHUSDT bucket start 900,000
        {"symbol": "ETHUSDT", "liquidation_side": "long_liquidation", "notional_usd": 400.0, "timestamp_ms": 1200000},
    ]

    # aggregate 15m (900,000 ms)
    windows = aggregate_forceorder_windows(rows, bucket_ms=900000, configured_lag_ms=60000)

    assert len(windows) == 3
    # Sorted by symbol, then bucket_start_ms

    # 1. BTCUSDT @ 900k
    assert windows[0]["symbol"] == "BTCUSDT"
    assert windows[0]["bucket_start_ms"] == 900000
    assert windows[0]["bucket_end_ms"] == 1800000
    assert windows[0]["available_at_ms"] == 1860000
    assert windows[0]["long_liquidation_notional_usd"] == 1500.0
    assert windows[0]["short_liquidation_notional_usd"] == 300.0
    assert windows[0]["total_liquidation_notional_usd"] == 1800.0
    assert windows[0]["event_count"] == 3

    # 2. BTCUSDT @ 1800k
    assert windows[1]["symbol"] == "BTCUSDT"
    assert windows[1]["bucket_start_ms"] == 1800000
    assert windows[1]["long_liquidation_notional_usd"] == 0.0
    assert windows[1]["short_liquidation_notional_usd"] == 2000.0
    assert windows[1]["event_count"] == 1

    # 3. ETHUSDT @ 900k
    assert windows[2]["symbol"] == "ETHUSDT"
    assert windows[2]["bucket_start_ms"] == 900000
    assert windows[2]["long_liquidation_notional_usd"] == 400.0
    assert windows[2]["short_liquidation_notional_usd"] == 0.0
    assert windows[2]["event_count"] == 1


def test_compute_concentration_stats():
    windows = [
        # 2026-06-01
        {"symbol": "BTCUSDT", "day_key": "2026-06-01", "event_count": 8, "total_liquidation_notional_usd": 800.0},
        {"symbol": "ETHUSDT", "day_key": "2026-06-01", "event_count": 2, "total_liquidation_notional_usd": 200.0},
        # 2026-06-02
        {"symbol": "BTCUSDT", "day_key": "2026-06-02", "event_count": 5, "total_liquidation_notional_usd": 500.0},
        # 2026-06-03
        {"symbol": "SOLUSDT", "day_key": "2026-06-03", "event_count": 5, "total_liquidation_notional_usd": 500.0},
    ]
    # Total windows = 4. Total event count = 20. Total notional = 2000.0
    # Day event counts: 2026-06-01: 10, 2026-06-02: 5, 2026-06-03: 5. Top 1 day: 10/20 = 0.5. Top 3 days: 20/20 = 1.0
    # Symbol event counts: BTCUSDT: 13, ETHUSDT: 2, SOLUSDT: 5. Top 1 symbol: 13/20 = 0.65
    # Day notional: 2026-06-01: 1000.0, 2026-06-02: 500.0, 2026-06-03: 500.0. Top 1 day: 1000/2000 = 0.5. Top 3 days: 2000/2000 = 1.0
    # Symbol notional: BTCUSDT: 1300.0, ETHUSDT: 200.0, SOLUSDT: 500.0. Top 1 symbol: 1300/2000 = 0.65. Top 3 symbols: 2000/2000 = 1.0

    stats = compute_concentration_stats(windows)

    # Event count share
    assert stats["event_count_concentration"]["top_1_day_event_share"] == 0.5
    assert stats["event_count_concentration"]["top_3_days_event_share"] == 1.0
    assert stats["event_count_concentration"]["top_1_symbol_event_share"] == 0.65
    assert stats["event_count_concentration"]["top_3_symbols_event_share"] == 1.0

    # Notional share
    assert stats["notional_concentration"]["top_1_day_notional_share"] == 0.5
    assert stats["notional_concentration"]["top_3_days_notional_share"] == 1.0
    assert stats["notional_concentration"]["top_1_symbol_notional_share"] == 0.65


def test_build_density_report_and_imbalance_distribution():
    parsed_rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": 1710000000000, "notional_usd": 1000.0},
        {"symbol": "BTCUSDT", "timestamp_ms": 1710000000000 + 15 * 24 * 60 * 60 * 1000, "notional_usd": 2000.0},
    ]
    # diff is 15 days
    windows_15m = [
        {"symbol": "BTCUSDT", "day_key": "2024-03-10", "event_count": 1, "total_liquidation_notional_usd": 1000.0, "long_liquidation_notional_usd": 1000.0, "short_liquidation_notional_usd": 0.0},
        {"symbol": "BTCUSDT", "day_key": "2024-03-25", "event_count": 1, "total_liquidation_notional_usd": 2000.0, "long_liquidation_notional_usd": 0.0, "short_liquidation_notional_usd": 2000.0},
    ]

    density = build_density_report(parsed_rows, windows_15m)
    assert density["liquidation_history_days"] == 15.0
    assert density["symbols_with_events"] == 1
    assert density["event_days"] == 2
    assert density["top_1_symbol_notional_share"] == 1.0

    imbalance = build_imbalance_distribution(windows_15m, windows_15m)  # pass same for simplicity
    assert imbalance["long_liquidation_notional_total"] == 1000.0
    assert imbalance["short_liquidation_notional_total"] == 2000.0
