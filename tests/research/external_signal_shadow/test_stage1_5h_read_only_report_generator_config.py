from configs import base


def test_stage1_5h_config_constants_exist_and_are_safe():
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_SPREAD_P95_BPS == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_BUY_SLIPPAGE_500USDT_P95_BPS == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_SELL_SLIPPAGE_500USDT_P95_BPS == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_BID_DEPTH_USDT_P05 == 5_000.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_ASK_DEPTH_USDT_P05 == 5_000.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_BOOK_AVAILABILITY_RATIO == 0.98
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_FIRST_VALID_BOOK_LATENCY_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_CONSERVATIVE_ROUND_TRIP_COST_BPS == 50.0
    # Reserved for a future event-family gate. Stage 1.5H v1 must not consume this value.
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_EVENT_FAMILY_SAMPLE_REQUIRED == 3


def test_stage1_5h_config_does_not_enable_trading():
    assert getattr(base, "RISK_LIVE_TRADING_ENABLED", False) is False
    assert not hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5H_PAPER_TRADING_ENABLED")
    assert not hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5H_LIVE_TRADING_ENABLED")
