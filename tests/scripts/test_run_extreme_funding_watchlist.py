from scripts.run_extreme_funding_watchlist import (
    build_snapshot,
    should_poll,
    summarize_reject_counts,
)


def test_should_poll_respects_interval():
    assert should_poll(last_poll_ts=0.0, now_ts=10.0, interval_sec=10) is True
    assert should_poll(last_poll_ts=5.0, now_ts=10.0, interval_sec=10) is False


def test_summarize_reject_counts_counts_reasons():
    summary = summarize_reject_counts(["premium_below_threshold", "api_stale", "api_stale"])
    assert summary == {"premium_below_threshold": 1, "api_stale": 2}


def test_build_snapshot_requires_no_private_fields():
    raw = {
        "symbol": "DOGE/USDT",
        "exchange": "binance",
        "timestamp_ms": 1,
        "mark_price": 0.25,
        "index_price": 0.249,
        "premium_index": 0.001,
        "estimated_funding_rate": 0.0008,
        "next_funding_time_ms": 100,
        "open_interest": 1000.0,
        "oi_change_1h_pct": 1.0,
        "volume_24h_usdt": 100000000.0,
        "mark_data_age_sec": 1.0,
        "oi_data_age_sec": 1.0,
        "apiKey": "must_drop",
        "secret": "must_drop",
    }

    snapshot = build_snapshot(raw)

    assert snapshot["symbol"] == "DOGE/USDT"
    assert "apiKey" not in snapshot
    assert "secret" not in snapshot
