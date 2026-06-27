from src.research.external_signal_shadow.stage1_5f_live_depth_observer_metrics import (
    parse_depth_payload,
)


def test_depth_snapshot_computes_spread_and_top_depth():
    payload = {
        "bids": [["100.0", "10.0"], ["99.0", "20.0"]],
        "asks": [["101.0", "5.0"], ["102.0", "15.0"]],
        "T": 1700000000000,
    }
    # Parse depth
    snap = parse_depth_payload("ABCUSDT", payload, fetched_at_ms=1700000005000)
    assert snap.symbol == "ABCUSDT"
    assert snap.best_bid == 100.0
    assert snap.best_ask == 101.0
    assert snap.spread_bps == pytest_approx((101.0 / 100.0 - 1) * 10000)
    assert snap.top_bid_depth_usdt == 100.0 * 10.0 + 99.0 * 20.0
    assert snap.top_ask_depth_usdt == 101.0 * 5.0 + 102.0 * 15.0
    assert snap.depth_status == "healthy"


def test_buy_slippage_uses_ask_vwap_vs_mid_price():
    # Asks:
    # 101.0 for 5.0 qty (notional = 505.0)
    # Target notional is 500 USDT.
    # It can be filled completely in the first level.
    # Quantity filled = 500 / 101 = 4.950495
    # VWAP = 101.0
    # Mid = (100 + 101)/2 = 100.5
    # Slippage = (101 / 100.5 - 1) * 10000 = 49.75 bps
    payload = {
        "bids": [["100.0", "10.0"]],
        "asks": [["101.0", "10.0"]],
        "T": 1700000000000,
    }
    snap = parse_depth_payload("ABCUSDT", payload, fetched_at_ms=1700000005000)
    assert snap.buy_slippage_bps == pytest_approx((101.0 / 100.5 - 1) * 10000)


def test_sell_slippage_uses_bid_vwap_vs_mid_price():
    # Bids:
    # 100.0 for 10.0 qty (notional = 1000.0)
    # Target notional is 500 USDT.
    # It can be filled in the first level. VWAP = 100.0.
    # Mid = 100.5
    # Slippage = (1 - 100 / 100.5) * 10000 = 49.75 bps
    payload = {
        "bids": [["100.0", "10.0"]],
        "asks": [["101.0", "10.0"]],
        "T": 1700000000000,
    }
    snap = parse_depth_payload("ABCUSDT", payload, fetched_at_ms=1700000005000)
    assert snap.sell_slippage_bps == pytest_approx((1 - 100.0 / 100.5) * 10000)


def test_slippage_for_500usdt_marks_insufficient_depth():
    # Asks: 101.0 for 1.0 qty (notional = 101.0)
    # Total ask depth is 101.0, which is < 500 USDT.
    payload = {
        "bids": [["100.0", "10.0"]],
        "asks": [["101.0", "1.0"]],
        "T": 1700000000000,
    }
    snap = parse_depth_payload("ABCUSDT", payload, fetched_at_ms=1700000005000)
    assert snap.slippage_status == "insufficient_depth"
    assert snap.buy_slippage_bps is None


def test_empty_book_marks_depth_status_invalid():
    payload = {
        "bids": [],
        "asks": [],
        "T": 1700000000000,
    }
    snap = parse_depth_payload("ABCUSDT", payload, fetched_at_ms=1700000005000)
    assert snap.depth_status == "invalid"
    assert snap.best_bid is None
    assert snap.best_ask is None
    assert snap.spread_bps is None


def test_zero_price_book_marks_depth_status_invalid():
    payload = {
        "bids": [["0.0", "10.0"]],
        "asks": [["101.0", "10.0"]],
        "T": 1700000000000,
    }
    snap = parse_depth_payload("ABCUSDT", payload, fetched_at_ms=1700000005000)
    assert snap.depth_status == "invalid"


def test_depth_timestamp_quality_local_fetch_time_only_when_exchange_time_missing():
    # Missing exchange timestamp T
    payload = {
        "bids": [["100.0", "10.0"]],
        "asks": [["101.0", "10.0"]],
    }
    snap = parse_depth_payload("ABCUSDT", payload, fetched_at_ms=1700000005000)
    assert snap.exchange_time_ms is None
    assert snap.fetched_at_ms == 1700000005000


# Helper for float comparison in pytest
def pytest_approx(val):
    import pytest
    return pytest.approx(val, abs=1e-5)
