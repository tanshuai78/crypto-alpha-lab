from src.research.external_signal_shadow.stage1_5e_execution_feasibility_depth import (
    compute_depth_metrics,
    load_historical_depth_snapshots,
    normalize_depth_timestamp_fields,
    normalize_orderbook_symbol,
)


def test_compute_depth_metrics_for_buy_side_500usdt():
    orderbook = {
        "bids": [["99.9", "100"], ["99.0", "100"]],
        "asks": [["100.1", "2"], ["100.2", "3"], ["101.0", "100"]],
    }

    metrics = compute_depth_metrics(orderbook, notional_usdt=500.0)

    assert metrics["spread_bps"] > 0
    assert metrics["top_0_5pct_ask_depth_usdt"] > 0
    assert metrics["top_1pct_ask_depth_usdt"] > metrics["top_0_5pct_ask_depth_usdt"]
    assert metrics["slippage_estimate_bps_for_500usdt_buy"] >= 0


def test_compute_depth_metrics_marks_insufficient_depth():
    orderbook = {
        "bids": [["99.9", "1"]],
        "asks": [["100.1", "0.1"]],
    }

    metrics = compute_depth_metrics(orderbook, notional_usdt=500.0)

    assert metrics["buy_depth_sufficient_for_500usdt"] is False
    assert metrics["depth_status"] == "insufficient_ask_depth"


def test_depth_timestamp_quality_local_fetch_time_only_when_exchange_time_missing():
    fields = normalize_depth_timestamp_fields({"lastUpdateId": 123}, fetched_at_ms=1_700_000_000_000)

    assert fields["depth_fetched_at_ms"] == 1_700_000_000_000
    assert fields["exchange_event_time_ms"] is None
    assert fields["exchange_transaction_time_ms"] is None
    assert fields["depth_snapshot_age_ms"] is None
    assert fields["depth_timestamp_quality"] == "local_fetch_time_only"


def test_normalize_orderbook_symbol_handles_cex_formats():
    assert normalize_orderbook_symbol("ETH/USDT") == "ETHUSDT"
    assert normalize_orderbook_symbol("SOL/USDT:USDT") == "SOLUSDT"
    assert normalize_orderbook_symbol("BTCUSDT") == "BTCUSDT"


def test_load_historical_depth_snapshots_matches_symbol_and_entry_time(tmp_path):
    depth_dir = tmp_path / "historical_orderbook"
    depth_dir.mkdir()
    (depth_dir / "binance_ETHUSDT_2026-06-07.jsonl").write_text(
        '{"timestamp": 1780790400149, "exchange": "binance", "symbol": "ETH/USDT", '
        '"bids": [[1569.68, 11.0]], "asks": [[1569.69, 35.0]]}\n'
    )
    candidates = [{
        "symbol": "ETHUSDT",
        "symbol_event_id": "evt-eth",
        "event_type": "futures_contract_launch",
        "signed_mode": "futures_launch_long_attention_diagnostic",
        "entry_delay_hours": 12,
        "filter_group": "G1_source_event_after_first_hour_delay",
        "entry_time_ms": 1780790400200,
    }]

    result = load_historical_depth_snapshots(depth_dir, candidates, match_window_ms=1_000)

    assert result["coverage"]["historical_orderbook_depth_available"] is True
    assert result["coverage"]["matched_snapshot_count"] == 1
    assert result["coverage"]["matched_candidate_event_count"] == 1
    assert result["depth_rows"][0]["symbol"] == "ETHUSDT"
    assert result["depth_rows"][0]["symbol_event_id"] == "evt-eth"
    assert result["depth_rows"][0]["depth_status"] == "depth_computed"
    assert result["depth_rows"][0]["depth_timestamp_quality"] == "historical_snapshot_time"


def test_load_historical_depth_snapshots_reports_no_symbol_overlap(tmp_path):
    depth_dir = tmp_path / "historical_orderbook"
    depth_dir.mkdir()
    (depth_dir / "binance_ETHUSDT_2026-06-07.jsonl").write_text(
        '{"timestamp": 1780790400149, "exchange": "binance", "symbol": "ETH/USDT", '
        '"bids": [[1569.68, 11.0]], "asks": [[1569.69, 35.0]]}\n'
    )
    candidates = [{
        "symbol": "GIGGLEUSDT",
        "symbol_event_id": "evt-giggle",
        "entry_time_ms": 1780790400200,
    }]

    result = load_historical_depth_snapshots(depth_dir, candidates, match_window_ms=1_000)

    assert result["coverage"]["historical_orderbook_depth_available"] is False
    assert result["coverage"]["candidate_symbol_overlap_count"] == 0
    assert result["coverage"]["matched_snapshot_count"] == 0
    assert result["depth_rows"] == []


def test_load_historical_depth_snapshots_skips_file_body_when_filename_symbols_do_not_overlap(tmp_path):
    depth_dir = tmp_path / "historical_orderbook"
    depth_dir.mkdir()
    (depth_dir / "binance_ETHUSDT_2026-06-07.jsonl").write_text("not-json\n")
    candidates = [{
        "symbol": "GIGGLEUSDT",
        "symbol_event_id": "evt-giggle",
        "entry_time_ms": 1780790400200,
    }]

    result = load_historical_depth_snapshots(depth_dir, candidates, match_window_ms=1_000)

    assert result["coverage"]["candidate_symbol_overlap_count"] == 0
    assert result["coverage"]["historical_depth_malformed_row_count"] == 0
    assert result["coverage"]["historical_depth_parsed_row_count"] == 0
