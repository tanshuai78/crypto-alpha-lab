from src.research.external_signal_shadow.stage1_5c1_price_coverage_builder import (
    build_event_coverage_report,
    compute_event_coverage_status,
    dedupe_kline_rows,
    filter_futures_coverage_pass_events,
    summarize_coverage_reports,
)


def _bar(symbol, t):
    return {
        "symbol": symbol,
        "bar_start_ms": t,
        "bar_end_ms": t + 900_000,
        "open": 1.0,
        "high": 1.0,
        "low": 1.0,
        "close": 1.0,
        "quote_volume": 1000.0,
        "source": "binance_um_futures_15m",
    }


def test_dedupe_kline_rows_by_symbol_and_bar_start():
    rows = [_bar("ABCUSDT", 0), _bar("ABCUSDT", 0), _bar("ABCUSDT", 900_000)]
    deduped = dedupe_kline_rows(rows)
    assert len(deduped) == 2


def test_futures_launch_passes_with_post_launch_forward_coverage_only():
    event = {
        "symbol_event_id": "f1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 0,
    }
    # 350 bars is enough for max_entry(12h) + max_forward(24h) + buffer(2d) = 84h = 336 bars
    bars = [_bar("ABCUSDT", i * 900_000) for i in range(0, 350)]
    status = compute_event_coverage_status(event, bars, futures_symbol_verified=True)
    assert status["futures_kline_status"] == "post_launch_futures_coverage_pass"
    assert status["stage1_5c_rerun_candidate"] is True


def test_delisting_requires_pre_event_history():
    event = {
        "symbol_event_id": "d1",
        "event_type": "exchange_delisting_notice",
        "symbol": "ABCUSDT",
        "available_at_ms": 35 * 24 * 3600_000,
    }
    # pre-event 30d needs bars. available_at is 35 days.
    # We generate bars from 0 to 39 days (needs to cover available_at + 3.5 days = 38.5 days).
    bars = [_bar("ABCUSDT", i * 900_000) for i in range(0, 39 * 24 * 4)]
    status = compute_event_coverage_status(event, bars, futures_symbol_verified=True)
    assert status["futures_kline_status"] == "futures_pre_event_coverage_pass"
    assert status["stage1_5c_rerun_candidate"] is True


def test_symbol_not_found_report_is_not_replay_candidate():
    event = {"symbol_event_id": "x", "event_type": "exchange_delisting_notice", "symbol": "XYZUSDT", "available_at_ms": 0}
    report = build_event_coverage_report(event, futures_bars=[], spot_bars=[], futures_symbol_verified=False, spot_symbol_verified=False)
    assert report["futures_symbol_status"] == "futures_symbol_current_exchangeinfo_not_found"
    assert report["stage1_5c_rerun_candidate"] is False
    assert report["spot_proxy_replay_allowed"] is False


def test_recent_event_forward_window_not_matured_not_failed():
    event = {"symbol_event_id": "f_recent", "event_type": "futures_contract_launch", "symbol": "ABCUSDT", "available_at_ms": 100_000_000}
    # Available at 100s, now is 101s, not enough to cover the window (max_entry + max_forward + buffer = 3.5 days = ~300k seconds)
    status = compute_event_coverage_status(event, [], futures_symbol_verified=True, current_time_ms=101_000_000)
    assert status["futures_kline_status"] in {"post_launch_futures_coverage_not_matured", "future_bar_request_truncated"}
    assert status["rerun_after_ms"] is not None


def test_futures_launch_outputs_first_futures_bar_anchor():
    event = {"symbol_event_id": "f_anchor", "event_type": "futures_contract_launch", "symbol": "ABCUSDT", "available_at_ms": 0}
    bars = [_bar("ABCUSDT", 3_600_000), _bar("ABCUSDT", 4_500_000)]
    status = compute_event_coverage_status(event, bars, futures_symbol_verified=True)
    assert status["first_futures_bar_start_ms"] == 3_600_000
    assert status["launch_price_anchor_status"] == "first_futures_bar_after_available_at"
    assert status["suggested_replay_anchor_ms"] >= 3_600_000


def test_spot_proxy_available_does_not_make_summary_ready():
    summary = summarize_coverage_reports([{
        "stage1_5c_rerun_candidate": False,
        "spot_proxy_status": "spot_proxy_available_report_only",
        "event_day": "2026-01-01",
        "symbol": "ABCUSDT",
        "futures_symbol_status": "futures_symbol_current_exchangeinfo_not_found",
        "futures_kline_status": "futures_symbol_not_found",
        "replay_price_source_allowed": "none",
        "event_type": "futures_contract_launch",
    }])
    assert summary["spot_proxy_available_event_count"] == 1
    assert summary["decision"] != "stage1_5c1_price_coverage_ready_for_1_5c_rerun"


def test_market_scope_unknown_blocks_rerun_candidate():
    event = {
        "symbol_event_id": "d_unknown",
        "event_type": "exchange_delisting_notice",
        "symbol": "ABCUSDT",
        "available_at_ms": 0,
        "title": "Binance Will Delist ABC"
    }
    report = build_event_coverage_report(event, futures_bars=[], spot_bars=[], futures_symbol_verified=True, spot_symbol_verified=False)
    assert report["market_scope_inferred"] in {"unknown", "spot", "um_futures", "cross_market"}
    if report["market_scope_inferred"] == "unknown":
        assert report["stage1_5c_rerun_candidate"] is False


def test_spot_delisting_never_becomes_futures_rerun_candidate():
    event = {
        "symbol_event_id": "d_spot",
        "event_type": "exchange_delisting_notice",
        "symbol": "ABCUSDT",
        "available_at_ms": 35 * 24 * 3600_000,
        "title": "Binance Will Delist ABC from Spot Trading",
    }
    bars = [_bar("ABCUSDT", i * 900_000) for i in range(0, 39 * 24 * 4)]
    report = build_event_coverage_report(
        event,
        futures_bars=bars,
        spot_bars=[],
        futures_symbol_verified=True,
        spot_symbol_verified=False,
    )
    assert report["market_scope_inferred"] == "spot"
    assert report["futures_kline_status"] == "futures_pre_event_coverage_pass"
    assert report["stage1_5c_rerun_candidate"] is False
    assert report["replay_price_source_allowed"] == "none"


def test_coverage_pass_events_include_anchor_and_coverage_metadata():
    event = {
        "symbol_event_id": "f_anchor",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 0,
    }
    report = {
        "symbol_event_id": "f_anchor",
        "stage1_5c_rerun_candidate": True,
        "replay_price_source_allowed": "futures_only",
        "futures_kline_status": "post_launch_futures_coverage_pass",
        "first_futures_bar_start_ms": 7_200_000,
        "first_futures_bar_after_available_at_ms": 7_200_000,
        "launch_price_anchor_status": "first_futures_bar_after_available_at",
        "suggested_replay_anchor_ms": 7_200_000,
        "market_scope_inferred": "um_futures",
    }
    rows = filter_futures_coverage_pass_events([event], [report])
    assert rows == [{**event, **{
        "stage1_5c_rerun_candidate": True,
        "replay_price_source_allowed": "futures_only",
        "futures_kline_status": "post_launch_futures_coverage_pass",
        "first_futures_bar_start_ms": 7_200_000,
        "first_futures_bar_after_available_at_ms": 7_200_000,
        "launch_price_anchor_status": "first_futures_bar_after_available_at",
        "suggested_replay_anchor_ms": 7_200_000,
        "market_scope_inferred": "um_futures",
    }}]
