import json

import pytest

from scripts.check_liquidation_collector_health import inspect_liquidation_collector_health


@pytest.fixture()
def healthy_archive_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # 1. Write raw events covering 25 hours with no duplicates, no invalid lines
    raw_path = data_dir / "trend_regime_force_orders_raw.jsonl"
    start_time = 1780000200000
    events = []
    for i in range(100):
        # space out events
        ts = start_time + i * 15 * 60 * 1000  # every 15 mins
        rec = {
            "schema_version": 1,
            "source": "binance_forceorder_ws",
            "event_id": f"binance_forceorder_ws|BTC/USDT|{ts}|{ts}|SELL|60000.0|0.1",
            "symbol": "BTC/USDT",
            "event_time_ms": ts,
            "trade_time_ms": ts,
            "side": "SELL",
            "liquidated_position_side": "long",
            "liquidation_side": "long_liquidation",
            "price": 60000.0,
            "quantity": 0.1,
            "notional_usdt": 6000.0,
        }
        events.append(rec)

    raw_path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

    # 2. Write 1m aggregated file covering trailing 24 hours with no missing buckets (1440 bars)
    # Let's say the current time is start_time + 99 * 15 * 60 * 1000
    current_time_ms = start_time + 99 * 15 * 60 * 1000
    agg_1m_path = data_dir / "trend_regime_liquidation_1m.jsonl"
    agg_rows = []

    # 24h lookback has 1440 minutes
    start_24h_ago = current_time_ms - 24 * 3600 * 1000
    for m in range(1440):
        bar_start = start_24h_ago + m * 60000
        agg_rows.append(
            {
                "symbol": "BTC/USDT",
                "bar_start_ms": bar_start,
                "long_liquidation_notional_1m_usdt": 0.0,
                "short_liquidation_notional_1m_usdt": 0.0,
                "total_liquidation_notional_1m_usdt": 0.0,
                "event_count_1m": 0,
                "source": "binance_forceorder_raw_archive",
                "filled_empty_bucket": True,
            }
        )
    agg_1m_path.write_text("\n".join(json.dumps(r) for r in agg_rows) + "\n", encoding="utf-8")

    # Also create empty 5m and 1h aggregated files so they "exist"
    (data_dir / "trend_regime_liquidation_5m.jsonl").write_text("", encoding="utf-8")
    (data_dir / "trend_regime_liquidation_hourly.jsonl").write_text("", encoding="utf-8")

    return data_dir, current_time_ms


def test_health_check_reports_healthy_archive(healthy_archive_dir):
    data_dir, current_time_ms = healthy_archive_dir
    summary = inspect_liquidation_collector_health(
        data_dir,
        now_ms=current_time_ms,
        expected_symbols=["BTC/USDT"],
    )

    assert summary["raw_exists"] is True
    assert summary["raw_latest_timestamp_ms"] == current_time_ms
    assert summary["raw_invalid_json_line_count"] == 0
    assert summary["raw_last_line_valid"] is True
    assert summary["raw_duplicate_event_count"] == 0
    assert summary["raw_time_span_hours"] > 24.0
    assert summary["aggregate_1m_exists"] is True
    assert summary["aggregate_1m_latest_bucket_ms"] == current_time_ms - 60_000
    assert summary["aggregate_5m_row_count"] == 0
    assert summary["aggregate_5m_latest_bucket_ms"] is None
    assert summary["aggregate_1h_row_count"] == 0
    assert summary["aggregate_1h_latest_bucket_ms"] is None
    assert summary["aggregate_1m_coverage_ratio_24h"] == pytest.approx(1.0)
    assert summary["aggregate_1m_missing_bucket_count_24h"] == 0
    assert (
        summary["aggregate_1m_max_gap_minutes_24h"] == 1
    )  # since step is 1m, distance between adjacent bars is 1m
    assert summary["aggregate_5m_exists"] is True
    assert summary["aggregate_1h_exists"] is True
    assert summary["research_ready_1m_24h"] is True


def test_health_check_reports_invalid_json_lines(healthy_archive_dir):
    data_dir, current_time_ms = healthy_archive_dir
    raw_path = data_dir / "trend_regime_force_orders_raw.jsonl"

    # Append invalid JSON and trailing whitespace/empty lines
    with open(raw_path, "a", encoding="utf-8") as fh:
        fh.write("{invalid_json_here\n")
        fh.write("\n")  # empty line should be ignored, not count as invalid

    summary = inspect_liquidation_collector_health(
        data_dir,
        now_ms=current_time_ms,
        expected_symbols=["BTC/USDT"],
    )
    assert summary["raw_invalid_json_line_count"] == 1
    assert summary["raw_last_line_valid"] is False  # because the last text line is invalid JSON


def test_health_check_reports_duplicate_events(healthy_archive_dir):
    data_dir, current_time_ms = healthy_archive_dir
    raw_path = data_dir / "trend_regime_force_orders_raw.jsonl"

    # Append duplicate event
    rec = {
        "schema_version": 1,
        "source": "binance_forceorder_ws",
        "event_id": "binance_forceorder_ws|BTC/USDT|1780000200000|1780000200000|SELL|60000.0|0.1",
        "symbol": "BTC/USDT",
        "event_time_ms": 1780000200000,
        "trade_time_ms": 1780000200000,
        "side": "SELL",
        "price": 60000.0,
        "quantity": 0.1,
        "notional_usdt": 6000.0,
    }
    with open(raw_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")

    summary = inspect_liquidation_collector_health(
        data_dir,
        now_ms=current_time_ms,
        expected_symbols=["BTC/USDT"],
    )
    assert summary["raw_duplicate_event_count"] == 1


def test_health_check_reports_gaps_and_low_coverage(healthy_archive_dir):
    data_dir, current_time_ms = healthy_archive_dir
    agg_1m_path = data_dir / "trend_regime_liquidation_1m.jsonl"

    # Let's delete some rows in 1m aggregated file to simulate a gap
    rows = []
    with open(agg_1m_path, encoding="utf-8") as fh:
        for line in fh:
            rows.append(json.loads(line))

    # Remove minutes 100 to 200 (101 bars missing)
    del rows[100:201]

    with open(agg_1m_path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    summary = inspect_liquidation_collector_health(
        data_dir,
        now_ms=current_time_ms,
        expected_symbols=["BTC/USDT"],
    )
    # Coverage should be (1440 - 101) / 1440 = 1339 / 1440 ~ 0.93
    assert summary["aggregate_1m_coverage_ratio_24h"] == pytest.approx(1339 / 1440)
    assert summary["aggregate_1m_missing_bucket_count_24h"] == 101

    # Gap is from minute 99 to 201, which is 102 minutes difference
    assert summary["aggregate_1m_max_gap_minutes_24h"] == 102

    # research_ready should be False because coverage ratio is below 0.99 or max gap exceeds threshold
    assert summary["research_ready_1m_24h"] is False


def test_health_check_marks_research_ready_false_without_24h_coverage(tmp_path):
    # Only raw events, no aggregated files
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "trend_regime_force_orders_raw.jsonl").write_text("", encoding="utf-8")

    summary = inspect_liquidation_collector_health(
        data_dir,
        now_ms=1780000000000,
        expected_symbols=["BTC/USDT"],
    )
    assert summary["research_ready_1m_24h"] is False


def test_health_check_marks_research_ready_false_when_one_symbol_is_missing(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    raw_path = data_dir / "trend_regime_force_orders_raw.jsonl"
    now_ms = 1780086600000
    start_24h_ago = now_ms - 24 * 3600 * 1000

    raw_rows = []
    for symbol in ("BTC/USDT", "ETH/USDT"):
        for minute in range(0, 24 * 60, 30):
            ts = start_24h_ago + minute * 60_000
            raw_rows.append(
                {
                    "schema_version": 1,
                    "source": "binance_forceorder_ws",
                    "event_id": f"{symbol}|{ts}",
                    "symbol": symbol,
                    "event_time_ms": ts,
                    "trade_time_ms": ts,
                    "side": "SELL",
                    "liquidated_position_side": "long",
                    "liquidation_side": "long_liquidation",
                    "price": 60000.0,
                    "quantity": 0.1,
                    "notional_usdt": 6000.0,
                }
            )
    raw_path.write_text("\n".join(json.dumps(r) for r in raw_rows) + "\n", encoding="utf-8")

    agg_1m_path = data_dir / "trend_regime_liquidation_1m.jsonl"
    agg_rows = []
    for minute in range(24 * 60):
        bar_start = start_24h_ago + minute * 60_000
        agg_rows.append(
            {
                "symbol": "BTC/USDT",
                "bar_start_ms": bar_start,
                "long_liquidation_notional_1m_usdt": 0.0,
                "short_liquidation_notional_1m_usdt": 0.0,
                "total_liquidation_notional_1m_usdt": 0.0,
                "event_count_1m": 0,
                "source": "binance_forceorder_raw_archive",
                "filled_empty_bucket": True,
            }
        )
    agg_1m_path.write_text("\n".join(json.dumps(r) for r in agg_rows) + "\n", encoding="utf-8")
    (data_dir / "trend_regime_liquidation_5m.jsonl").write_text("", encoding="utf-8")
    (data_dir / "trend_regime_liquidation_hourly.jsonl").write_text("", encoding="utf-8")

    summary = inspect_liquidation_collector_health(
        data_dir,
        now_ms=now_ms,
        expected_symbols=["BTC/USDT", "ETH/USDT"],
    )
    assert summary["aggregate_1m_symbol_stats_24h"]["BTC/USDT"]["coverage_ratio"] == pytest.approx(1.0)
    assert summary["aggregate_1m_symbol_stats_24h"]["ETH/USDT"]["coverage_ratio"] == pytest.approx(0.0)
    assert summary["research_ready_1m_24h"] is False
