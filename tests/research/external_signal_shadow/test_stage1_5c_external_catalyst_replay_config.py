from configs import base


def test_stage1_5c_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_INTERVAL_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_P95_MAX_INTERVAL_MS == 30 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_MIN_PRE_EVENT_PRICE_HISTORY_DAYS == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_ENTRY_DELAY_HOURS == (1, 4, 12)
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_ENTRY_DELAY_HOURS == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_FORWARD_WINDOWS_HOURS == (1, 4, 12, 24)
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_FORWARD_WINDOW_HOURS == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_COST_SCENARIOS_BPS == (30, 50, 80)
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_COST_BPS == 50
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_RANDOM_BASELINE_TRIALS == 500
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_RANDOM_BASELINE_SEED == 42
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_LEFT_TAIL_PERCENTILE == 5
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_EVENT_COOLDOWN_HOURS == 24
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_MAX_SINGLE_SYMBOL_EVENT_SHARE == 0.50
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_ALLOWED_EVENT_TYPES == (
        "exchange_delisting_notice",
        "futures_contract_launch",
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_FILTER_GROUPS == (
        "G1_source_event_after_first_hour_delay",
        "G2_price_coverage_only",
        "G3_price_coverage_plus_liquidity_proxy",
    )
