import configs.base as cfg


def test_liquidation_shock_config_constants_exist():
    # Absolute thresholds
    assert hasattr(cfg, "LIQUIDATION_SHOCK_1M_MAJOR_ABS_THRESHOLD_USDT")
    assert isinstance(cfg.LIQUIDATION_SHOCK_1M_MAJOR_ABS_THRESHOLD_USDT, float)
    assert cfg.LIQUIDATION_SHOCK_1M_MAJOR_ABS_THRESHOLD_USDT > 0

    assert hasattr(cfg, "LIQUIDATION_SHOCK_1M_ALT_ABS_THRESHOLD_USDT")
    assert isinstance(cfg.LIQUIDATION_SHOCK_1M_ALT_ABS_THRESHOLD_USDT, float)
    assert cfg.LIQUIDATION_SHOCK_1M_ALT_ABS_THRESHOLD_USDT > 0

    # Relative score (percentile rank)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_1M_RELATIVE_SCORE_THRESHOLD")
    assert isinstance(cfg.LIQUIDATION_SHOCK_1M_RELATIVE_SCORE_THRESHOLD, float)
    assert 0.0 < cfg.LIQUIDATION_SHOCK_1M_RELATIVE_SCORE_THRESHOLD <= 1.0

    # Lookback window
    assert hasattr(cfg, "LIQUIDATION_SHOCK_1M_LOOKBACK_HOURS")
    assert isinstance(cfg.LIQUIDATION_SHOCK_1M_LOOKBACK_HOURS, int)
    assert cfg.LIQUIDATION_SHOCK_1M_LOOKBACK_HOURS > 0

    # Required reference bars
    assert hasattr(cfg, "LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS")
    assert isinstance(cfg.LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS, int)
    assert cfg.LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS > 0

    # Dominance ratio filter
    assert hasattr(cfg, "LIQUIDATION_SHOCK_1M_DOMINANCE_RATIO_MIN")
    assert isinstance(cfg.LIQUIDATION_SHOCK_1M_DOMINANCE_RATIO_MIN, float)
    assert 0.5 <= cfg.LIQUIDATION_SHOCK_1M_DOMINANCE_RATIO_MIN <= 1.0

    # Deduplication bucket size
    assert hasattr(cfg, "LIQUIDATION_SHOCK_1M_DEDUP_BUCKET_MINUTES")
    assert isinstance(cfg.LIQUIDATION_SHOCK_1M_DEDUP_BUCKET_MINUTES, int)
    assert cfg.LIQUIDATION_SHOCK_1M_DEDUP_BUCKET_MINUTES > 0

    # Response horizons
    assert hasattr(cfg, "LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES")
    assert isinstance(cfg.LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES, tuple)
    assert len(cfg.LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES) > 0
    assert all(isinstance(x, int) for x in cfg.LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES)

    # Direction min move in bps
    assert hasattr(cfg, "LIQUIDATION_SHOCK_DIRECTION_MIN_MOVE_BPS")
    assert isinstance(cfg.LIQUIDATION_SHOCK_DIRECTION_MIN_MOVE_BPS, float)
    assert cfg.LIQUIDATION_SHOCK_DIRECTION_MIN_MOVE_BPS >= 0

    # Feasibility metrics
    assert hasattr(cfg, "LIQUIDATION_SHOCK_FEASIBILITY_MIN_COVERAGE_RATIO")
    assert isinstance(cfg.LIQUIDATION_SHOCK_FEASIBILITY_MIN_COVERAGE_RATIO, float)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_FEASIBILITY_MAX_GAP_MINUTES")
    assert isinstance(cfg.LIQUIDATION_SHOCK_FEASIBILITY_MAX_GAP_MINUTES, int)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_FEASIBILITY_MIN_EVAL_HOURS")
    assert isinstance(cfg.LIQUIDATION_SHOCK_FEASIBILITY_MIN_EVAL_HOURS, float)

    # Review criteria
    assert hasattr(cfg, "LIQUIDATION_SHOCK_MIN_TOTAL_EVENTS")
    assert isinstance(cfg.LIQUIDATION_SHOCK_MIN_TOTAL_EVENTS, int)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_MIN_EVENTS_PER_24H")
    assert isinstance(cfg.LIQUIDATION_SHOCK_MIN_EVENTS_PER_24H, float)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_MIN_POSITIVE_SYMBOL_COUNT")
    assert isinstance(cfg.LIQUIDATION_SHOCK_MIN_POSITIVE_SYMBOL_COUNT, int)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_MAX_SINGLE_SYMBOL_EVENT_SHARE")
    assert isinstance(cfg.LIQUIDATION_SHOCK_MAX_SINGLE_SYMBOL_EVENT_SHARE, float)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_MIN_DIRECTIONAL_BIAS")
    assert isinstance(cfg.LIQUIDATION_SHOCK_MIN_DIRECTIONAL_BIAS, float)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_MIN_MINMOVE_DIRECTIONAL_BIAS")
    assert isinstance(cfg.LIQUIDATION_SHOCK_MIN_MINMOVE_DIRECTIONAL_BIAS, float)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_MIN_ADJACENT_HORIZON_PASS_COUNT")
    assert isinstance(cfg.LIQUIDATION_SHOCK_MIN_ADJACENT_HORIZON_PASS_COUNT, int)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_MIN_SYMBOL_EVENTS")
    assert isinstance(cfg.LIQUIDATION_SHOCK_MIN_SYMBOL_EVENTS, int)
    assert hasattr(cfg, "LIQUIDATION_SHOCK_MIN_ABS_MEDIAN_RESPONSE_BPS")
    assert isinstance(cfg.LIQUIDATION_SHOCK_MIN_ABS_MEDIAN_RESPONSE_BPS, float)
