from research.external_signal_shadow.stage1_4b_lite_models import CandidateEvent
from research.external_signal_shadow.stage1_4b_lite_replay import replay_event


def test_replay_event_computes_signed_terminal_return_after_cost():
    event = CandidateEvent(
        candidate_name="oi_expansion_trend_confirmation",
        symbol="BTCUSDT",
        event_time_ms=1000,
        event_available_at_ms=1000,
        entry_bar_start_ms=2000,
        signed_direction=1, # Long
        metadata={}
    )

    # 15m bars. i + 16 is exit bar.
    price_bars = [
        {"symbol": "BTCUSDT", "bar_start_ms": 2000 + i * 900000, "close_price": 100.0 + i}
        for i in range(20)
    ]

    # entry_bar is at 2000 (i=0, close_price=100.0)
    # exit_bar (i=16) is at 2000 + 16*900000 = 14402000 (close_price=116.0)
    # raw_return = (116 - 100) / 100 = 0.16 (16%)
    # signed_return = 0.16 * 1 = 1600 bps
    # net return after 50bps = 1600 - 50 = 1550 bps
    res = replay_event(event, price_bars)
    assert res is not None
    assert res["terminal_return_4h_net_bps_after_50bps"] == 1550.0
    assert res["terminal_return_4h_net_bps_after_30bps"] == 1570.0
    assert res["terminal_return_4h_net_bps_after_80bps"] == 1520.0
    assert res["signed_short_replay_present"] is False
    assert res["short_execution_intent_allowed"] is False
    assert res["borrow_or_margin_feasibility_checked"] is False


def test_replay_event_skips_when_forward_window_incomplete():
    event = CandidateEvent(
        candidate_name="oi_expansion_trend_confirmation",
        symbol="BTCUSDT",
        event_time_ms=1000,
        event_available_at_ms=1000,
        entry_bar_start_ms=2000,
        signed_direction=1,
        metadata={}
    )

    # only 10 bars -> not enough for 4h (16 bars)
    price_bars = [
        {"symbol": "BTCUSDT", "bar_start_ms": 2000 + i * 900000, "close_price": 100.0}
        for i in range(10)
    ]
    res = replay_event(event, price_bars)
    assert res is None
