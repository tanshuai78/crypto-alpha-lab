from configs import base


def test_trend_regime_phase1a_config_values_are_defined():
    assert base.TREND_REGIME_WATCH_SYMBOLS == (
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "XRP/USDT",
        "DOGE/USDT",
    )
    assert base.TREND_REGIME_MAJOR_SYMBOLS == ("BTC/USDT", "ETH/USDT")
    assert base.TREND_REGIME_LARGE_ALT_SYMBOLS == ("SOL/USDT", "XRP/USDT", "DOGE/USDT")
    assert base.TREND_REGIME_VOL_BREAKOUT_MULTIPLIER == 2.5
    assert base.TREND_REGIME_MAX_HOLDING_HOURS == 12
    assert base.TREND_REGIME_STOP_LOSS_PCT == 1.5
    assert base.TREND_REGIME_MIN_1H_ABS_RETURN_PCT_MAJOR == 2.0
    assert base.TREND_REGIME_MIN_1H_ABS_RETURN_PCT_LARGE_ALT == 2.5
    assert base.TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_MAJOR == 1.5
    assert base.TREND_REGIME_MIN_OI_CONFIRMATION_1H_PCT_LARGE_ALT == 2.0
    assert base.TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_MAJOR == 10_000_000.0
    assert base.TREND_REGIME_LIQUIDATION_NOTIONAL_MIN_USDT_LARGE_ALT == 3_000_000.0
    assert base.TREND_REGIME_MIN_24H_VOLUME_USDT == 300_000_000.0
    assert base.TREND_REGIME_MAX_DATA_AGE_SEC == 30
    assert base.TREND_REGIME_OBSERVATION_COST_BPS == 30.0
    assert base.TREND_REGIME_STRESS_COST_BPS == 50.0
    assert base.TREND_REGIME_MAX_SLIPPAGE_BPS == 8.0
    assert base.TREND_REGIME_EVENT_LOG_JSONL == "trend_regime_watch_events.jsonl"
