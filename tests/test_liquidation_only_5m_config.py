import configs.base as cfg


def test_liquidation_only_5m_config_constants_exist():
    assert hasattr(cfg, "LIQUIDATION_ONLY_5M_MAJOR_ABS_THRESHOLD_USDT")
    assert hasattr(cfg, "LIQUIDATION_ONLY_5M_ALT_ABS_THRESHOLD_USDT")
    assert hasattr(cfg, "LIQUIDATION_ONLY_5M_RELATIVE_SCORE_THRESHOLD")
    assert hasattr(cfg, "LIQUIDATION_ONLY_5M_ROLLING_LOOKBACK_DAYS")
    assert hasattr(cfg, "LIQUIDATION_ONLY_5M_FORWARD_HORIZONS_BARS")
    assert hasattr(cfg, "LIQUIDATION_ONLY_5M_DOMINANCE_RATIO_MIN")
    assert hasattr(cfg, "LIQUIDATION_ONLY_5M_ASSUMED_MIN_ROUND_TRIP_COST_BPS")


def test_liquidation_only_5m_config_constants_types():
    assert isinstance(cfg.LIQUIDATION_ONLY_5M_MAJOR_ABS_THRESHOLD_USDT, float)
    assert isinstance(cfg.LIQUIDATION_ONLY_5M_ALT_ABS_THRESHOLD_USDT, float)
    assert isinstance(cfg.LIQUIDATION_ONLY_5M_RELATIVE_SCORE_THRESHOLD, float)
    assert isinstance(cfg.LIQUIDATION_ONLY_5M_ROLLING_LOOKBACK_DAYS, int)
    assert isinstance(cfg.LIQUIDATION_ONLY_5M_FORWARD_HORIZONS_BARS, (list, tuple))
    assert isinstance(cfg.LIQUIDATION_ONLY_5M_DOMINANCE_RATIO_MIN, float)
    assert isinstance(cfg.LIQUIDATION_ONLY_5M_ASSUMED_MIN_ROUND_TRIP_COST_BPS, float)
