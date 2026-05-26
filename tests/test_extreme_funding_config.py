from configs import base


def test_extreme_funding_phase1a_config_constants_exist():
    assert base.EXTREME_FUNDING_WATCH_SYMBOLS == (
        "XRP/USDT",
        "DOGE/USDT",
        "ADA/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "BTC/USDT",
    )
    assert base.EXTREME_FUNDING_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT == 30.0
    assert base.EXTREME_FUNDING_STRONG_PRE_SIGNAL_ANNUALIZED_THRESHOLD_PCT == 50.0
    assert base.EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT == 100.0
    assert base.EXTREME_FUNDING_MICRO_PERSISTENCE_WINDOW_MIN == 30
    assert base.EXTREME_FUNDING_MICRO_PERSISTENCE_MIN == 0.70
    assert base.EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_WEAK == 0.50
    assert base.EXTREME_FUNDING_OI_CONFIRMATION_MIN_CHANGE_1H_PCT == 0.0
    assert base.EXTREME_FUNDING_OI_STRONG_CONFIRMATION_MIN_CHANGE_1H_PCT == 3.0
    assert base.EXTREME_FUNDING_MARK_DATA_POLL_INTERVAL_SEC == 10
    assert base.EXTREME_FUNDING_OI_POLL_INTERVAL_SEC == 60
    assert base.EXTREME_FUNDING_KLINE_REFRESH_INTERVAL_SEC == 3600
    assert base.EXTREME_FUNDING_HEARTBEAT_INTERVAL_SEC == 300
    assert base.EXTREME_FUNDING_MAX_MARK_DATA_AGE_SEC == 30
    assert base.EXTREME_FUNDING_MAX_OI_DATA_AGE_SEC == 180


def test_extreme_funding_phase1a_live_polling_config_constants_exist():
    assert base.EXTREME_FUNDING_BINANCE_FAPI_BASE_URL == "https://fapi.binance.com"
    assert base.EXTREME_FUNDING_HTTP_TIMEOUT_SEC == 10.0
    assert base.EXTREME_FUNDING_LOCAL_DRY_RUN_MAX_ITERATIONS == 3
    assert base.EXTREME_FUNDING_OI_CHANGE_LOOKBACK_SEC == 3600
    assert base.EXTREME_FUNDING_LOOP_ERROR_BACKOFF_SEC == 5.0
    assert base.EXTREME_FUNDING_MICRO_PERSISTENCE_MIN_COVERAGE_SEC == 300
    assert base.EXTREME_FUNDING_EVENT_LOG_JSONL == "extreme_funding_watch_events.jsonl"


def test_extreme_funding_phase1b_candidate_config_values_are_defined():
    assert base.EXTREME_FUNDING_MIN_NET_EDGE_BPS == 30.0
    assert base.EXTREME_FUNDING_BASIS_ABSORPTION_MAX_RATIO == 0.50
    assert base.EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS == 1
    assert base.EXTREME_FUNDING_MIN_EXPECTED_FUNDING_INCOME_BPS == 50.0
    assert base.EXTREME_FUNDING_FEE_BPS == 8.0
    assert base.EXTREME_FUNDING_SLIPPAGE_RESERVE_BPS == 8.0
    assert base.EXTREME_FUNDING_ROLLBACK_RESERVE_BPS == 10.0
    assert base.EXTREME_FUNDING_MAX_SLIPPAGE_BPS == 10.0


def test_extreme_funding_phase1c_shadow_config_values_are_defined():
    assert base.EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS == 3
    assert base.EXTREME_FUNDING_SHADOW_EXIT_ANNUALIZED_BELOW_PCT == 15.0
    assert base.EXTREME_FUNDING_SHADOW_BASIS_LOSS_HALT_RATIO == 0.50


def test_extreme_funding_historical_basis_replay_config_values_are_defined():
    assert base.EXTREME_FUNDING_BASIS_REPLAY_INTERVAL == "1m"
    assert base.EXTREME_FUNDING_BASIS_REPLAY_ALIGNMENT_TOLERANCE_MS == 120_000
    assert base.EXTREME_FUNDING_BASIS_REPLAY_REQUEST_WINDOW_MS == 300_000
    assert base.EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC == 20.0
    assert base.EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC == 0.2
    assert base.EXTREME_FUNDING_BASIS_REPLAY_STATIC_DEPTH_MULTIPLIER == 2.0
    assert base.EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR == "reports/extreme_funding"


def test_extreme_funding_sensitivity_audit_config_defined():
    assert base.EXTREME_FUNDING_SENSITIVITY_ANNUALIZED_GRID_PCT == (80.0, 100.0, 120.0)
    assert base.EXTREME_FUNDING_SENSITIVITY_MIN_INCOME_GRID_BPS == (30.0, 50.0, 70.0)
    assert base.EXTREME_FUNDING_SENSITIVITY_MAX_SLIPPAGE_GRID_BPS == (8.0, 10.0, 12.0)
    assert base.EXTREME_FUNDING_SENSITIVITY_EXPECTED_INTERVAL_GRID == (1, 2)
    assert base.EXTREME_FUNDING_SENSITIVITY_BASIS_ABSORPTION_GRID == (0.30, 0.50, 0.70)


def test_extreme_funding_admission_definition_config_defined():
    assert base.EXTREME_FUNDING_ANCHOR_ANNUALIZED_THRESHOLD_PCT == 100.0
    assert base.EXTREME_FUNDING_RESEARCH_MIN_GROSS_FUNDING_BPS == 15.0
    assert base.EXTREME_FUNDING_RESEARCH_BASIS_ABSORPTION_MAX_RATIO == 0.70
    assert base.EXTREME_FUNDING_TRADE_EXPECTED_HOLDING_INTERVALS == 1
