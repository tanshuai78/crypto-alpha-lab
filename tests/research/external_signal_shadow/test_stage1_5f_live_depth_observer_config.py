import math

from configs import base


def test_stage1_5f_config_constants_exist():
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_BINANCE_FAPI_BASE_URL")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_PATH")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_PATH")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_LIMIT")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COVERAGE_RATIO")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_SNAPSHOT_GAP_MS")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_ACTIVE_EVENT_SYMBOLS")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_DEPTH_REQUESTS_PER_MINUTE")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MIN_REQUEST_SUCCESS_RATE")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_CONSECUTIVE_NETWORK_ERRORS")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_HTTP_TIMEOUT_SEC")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_REFRESH_SEC")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_SLIPPAGE_NOTIONAL_USDT")
    assert hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_WATERMARK_VERSION")


def test_depth_limit_large_enough_for_top_20_metrics():
    # Binance depth limit must be at least 100 to calculate spread, top-depth, slippage properly
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_LIMIT >= 100


def test_min_snapshot_count_computed_from_window_poll_interval_and_coverage_ratio():
    expected_snapshot_count = math.floor(
        base.EXTERNAL_SIGNAL_STAGE1_5F_OBSERVATION_WINDOW_MS
        / (base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC * 1000)
    )
    min_snapshot_count = math.floor(
        expected_snapshot_count * base.EXTERNAL_SIGNAL_STAGE1_5F_MIN_SNAPSHOT_COVERAGE_RATIO
    )
    # default should be floor(720 * 0.80) = 576
    assert expected_snapshot_count == 720
    assert min_snapshot_count == 576


def test_max_snapshot_gap_is_consistent_with_coverage_ratio_and_poll_interval():
    # max snapshot gap (5min) must be larger than poll interval (60s) but reasonably small
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_SNAPSHOT_GAP_MS > base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_POLL_INTERVAL_SEC * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_SNAPSHOT_GAP_MS == 5 * 60 * 1000


def test_request_success_rate_threshold_exists():
    assert 0.0 <= base.EXTERNAL_SIGNAL_STAGE1_5F_MIN_REQUEST_SUCCESS_RATE <= 1.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5F_MIN_REQUEST_SUCCESS_RATE == 0.95
