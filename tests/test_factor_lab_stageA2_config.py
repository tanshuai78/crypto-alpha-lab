import configs.base as cfg


def test_stageA2_regime_config_values_are_locked():
    assert cfg.FACTOR_LAB_STAGEA2_BTC_MA_DAYS == 20
    assert cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_RETURN_DAYS == 20
    assert cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_COVERAGE_RATIO == 0.80
    assert cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_SYMBOLS == cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N
    assert cfg.FACTOR_LAB_STAGEA2_MIN_DRAWDOWN_REDUCTION_PCT == 30.0
    assert cfg.FACTOR_LAB_STAGEA2_MAX_CASH_DAYS_SHARE == 0.60
    assert cfg.FACTOR_LAB_STAGEA2_MAX_BENCHMARK_UNDERPERFORMANCE_PCT == 10.0
    assert cfg.FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT == cfg.FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT


def test_stageA2_allowed_variants_are_narrowed_to_round1_scope():
    assert cfg.FACTOR_LAB_STAGEA2_ALLOWED_VARIANTS == (
        "regime_none",
        "btc_ma20_cash",
        "alt_universe_20d_return_cash",
    )
