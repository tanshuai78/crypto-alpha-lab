from configs import base


def test_stage1_5b_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_MIN_ARTICLE_EVENTS == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_TARGET_MAX_ARTICLE_EVENTS_FIRST_PASS == 100
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_MIN_UNIQUE_EVENT_DAYS == 20
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_MIN_SYMBOLS_WITH_EVENTS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_PRIMARY_ANNOUNCEMENT_DELAY_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5B_ALLOWED_EVENT_TYPES == (
        "exchange_delisting_notice",
        "futures_contract_launch",
    )
    assert "margin_enablement" not in base.EXTERNAL_SIGNAL_STAGE1_5B_ALLOWED_EVENT_TYPES
