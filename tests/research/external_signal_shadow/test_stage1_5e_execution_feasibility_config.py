from configs import base


def test_stage1_5e_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_EVENT_TYPE == "futures_contract_launch"
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_SIGNED_MODE == "futures_launch_long_attention_diagnostic"
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_ENTRY_DELAY_HOURS == 12
    assert "G1_source_event_after_first_hour_delay" in base.EXTERNAL_SIGNAL_STAGE1_5E_PRIMARY_FILTER_GROUPS
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MIN_AUDIT_EVENT_COUNT >= 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MAX_LIVE_SPREAD_BPS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MAX_SLIPPAGE_BPS_FOR_500USDT > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MIN_QUOTE_VOLUME_PASS_RATE == 0.70
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_P95_RANGE_MULTIPLIER_BLOCK == 2.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_HISTORICAL_DEPTH_MATCH_WINDOW_MS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_DEPTH_PATH == "/fapi/v1/depth"
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_MARK_PRICE_KLINES_PATH == "/fapi/v1/markPriceKlines"
    assert base.EXTERNAL_SIGNAL_STAGE1_5E_PREMIUM_INDEX_KLINES_PATH == "/fapi/v1/premiumIndexKlines"
