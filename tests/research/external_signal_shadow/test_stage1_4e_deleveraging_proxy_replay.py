import pytest

from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    CANDIDATE_15M,
    ProxyEvent,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_replay import (
    replay_deleveraging_proxy_events,
)

# Multiples of 900000 (15m)
T_START = 1600000200000
T_END = T_START + 900000
T_AVAILABLE = T_END + 300000 # Lag of 5 mins

# Entry bar starts at first bar >= T_AVAILABLE.
# Let's say we have 15m price bars starting at:
# Bar 0: T_START (1600000200000)
# Bar 1: T_END (1600001100000)
# Bar 2: T_END + 900000 (1600002000000) -> this is >= T_AVAILABLE (1600001400000)
# So Bar 2 is the entry bar!

def test_signed_replay_computes_correct_forward_returns():
    # Long event: signed_direction = 1
    event = ProxyEvent(
        symbol="BTCUSDT",
        candidate_name=CANDIDATE_15M,
        event_label="down_flush_deleveraging_proxy",
        signed_direction=1,
        bucket_start_ms=T_START,
        bucket_end_ms=T_END,
        event_time_ms=T_END,
        event_available_at_ms=T_AVAILABLE,
        entry_bar_start_ms=None,
        price_return=-0.02,
        oi_change=-0.04,
        oi_start=100.0,
        oi_end=96.0,
        source="oi_and_price_joint",
        source_quality="15m_aligned_tick"
    )

    # We need price bars.
    # Entry bar (Bar 2) starts at T_ENTRY = 1600002000000. Open price is 100.0.
    # 1h later: T_ENTRY + 3600000 = 1600005600000.
    # Let's add a bar at T_ENTRY + 3600000 with close price 102.0 (+2%).
    # 4h later: T_ENTRY + 14400000 = 1600016400000 with close price 105.0 (+5%).
    # 12h later: T_ENTRY + 43200000 = 1600045200000 with close price 98.0 (-2%).
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 100.0, "low": 98.0, "close": 98.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END, "open": 98.0, "high": 98.0, "low": 98.0, "close": 98.0},
        {"symbol": "BTCUSDT", "bar_start_ms": 1600002000000, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
        {"symbol": "BTCUSDT", "bar_start_ms": 1600002000000 + 3600000, "open": 100.0, "high": 102.0, "low": 100.0, "close": 102.0},
        {"symbol": "BTCUSDT", "bar_start_ms": 1600002000000 + 14400000, "open": 100.0, "high": 105.0, "low": 100.0, "close": 105.0},
        {"symbol": "BTCUSDT", "bar_start_ms": 1600002000000 + 43200000, "open": 100.0, "high": 100.0, "low": 98.0, "close": 98.0},
    ]

    replayed = replay_deleveraging_proxy_events([event], price_rows)
    assert len(replayed) == 3 # 1h, 4h, 12h

    # 1h window: gross return is 2% (200 bps). After 50 bps fee, net return is 150 bps.
    r1h = [r for r in replayed if r["forward_window_hours"] == 1][0]
    assert r1h["gross_return_bps"] == pytest.approx(200.0)
    assert r1h["net_return_bps_after_50bps"] == pytest.approx(150.0)

    # 4h window: gross return is 5% (500 bps). After 50 bps fee, net return is 450 bps.
    r4h = [r for r in replayed if r["forward_window_hours"] == 4][0]
    assert r4h["gross_return_bps"] == pytest.approx(500.0)
    assert r4h["net_return_bps_after_50bps"] == pytest.approx(450.0)

    # 12h window: gross return is -2% (-200 bps). After 50 bps fee, net return is -250 bps.
    r12h = [r for r in replayed if r["forward_window_hours"] == 12][0]
    assert r12h["gross_return_bps"] == pytest.approx(-200.0)
    assert r12h["net_return_bps_after_50bps"] == pytest.approx(-250.0)


def test_entry_bar_does_not_use_event_bar_close_to_prevent_lookahead():
    # Verify that entry_bar is indeed the first bar starting >= T_AVAILABLE,
    # NOT the event bucket's bar.
    event = ProxyEvent(
        symbol="BTCUSDT",
        candidate_name=CANDIDATE_15M,
        event_label="down_flush_deleveraging_proxy",
        signed_direction=1,
        bucket_start_ms=T_START,
        bucket_end_ms=T_END,
        event_time_ms=T_END,
        event_available_at_ms=T_AVAILABLE,
        entry_bar_start_ms=None,
        price_return=-0.02,
        oi_change=-0.04,
        oi_start=100.0,
        oi_end=96.0,
        source="oi_and_price_joint",
        source_quality="15m_aligned_tick"
    )
    # The event is from T_START to T_END. The close price of that bucket is 98.0.
    # The available_at is T_AVAILABLE (T_END + 5m).
    # The first price bar starting >= T_AVAILABLE starts at T_END + 15m = 1600002000000.
    # Its open price is 100.0.
    # If lookahead bias is present, it might use 98.0 or 100.0 incorrectly.
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 100.0, "low": 98.0, "close": 98.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END, "open": 98.0, "high": 98.0, "low": 98.0, "close": 98.0},
        {"symbol": "BTCUSDT", "bar_start_ms": 1600002000000, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
        {"symbol": "BTCUSDT", "bar_start_ms": 1600002000000 + 3600000, "open": 100.0, "high": 102.0, "low": 100.0, "close": 102.0},
    ]
    replayed = replay_deleveraging_proxy_events([event], price_rows)
    assert len(replayed) > 0
    # Entry price used should be 100.0 (from entry bar open), NOT 98.0 (from event close).
    r1h = [r for r in replayed if r["forward_window_hours"] == 1][0]
    assert r1h["entry_price"] == 100.0
