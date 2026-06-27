from src.research.external_signal_shadow.stage1_5f_live_depth_observer_budget import (
    can_start_new_observation,
    classify_budget_status,
    estimate_requests_per_min,
)


def test_new_event_skipped_when_request_budget_full():
    # If starting a new event would exceed max requests per minute (60)
    # Using 10s poll interval (6 polls per min):
    # At active_count = 9, we make 54 requests/min + 0.2. Adding 1 makes it 10 active (60.2 requests/min), exceeding 60.
    est = estimate_requests_per_min(9, 1, 10, 0.2)
    assert est == 54.2
    assert can_start_new_observation(9, est) is True

    # 10 active symbols -> 60.2 requests/min.
    est_next = estimate_requests_per_min(10, 1, 10, 0.2)
    assert est_next > 60.0
    assert can_start_new_observation(10, est_next) is False


def test_active_symbols_cannot_exceed_max_active_event_symbols():
    # Max active symbols is 30.
    # Even if requests are small (e.g. 10s poll but only 29 active), we can add 1.
    # If active_count is 30, we cannot start any more observations regardless of request budget.
    assert can_start_new_observation(29, 29.2) is True
    assert can_start_new_observation(30, 30.2) is False


def test_estimated_requests_per_min_accounts_for_poll_interval():
    # 10 active, poll interval 30s (2 polls per minute) -> 20 requests/min
    est = estimate_requests_per_min(10, 1, 30, 0.2)
    assert est == 20.2


def test_exchangeinfo_refresh_request_budget_is_included():
    # exchangeInfo refresh request budget is 1 request / 5 min = 0.2 requests/min
    est = estimate_requests_per_min(0, 1, 60, 0.2)
    assert est == 0.2

    # Classify budget status
    assert classify_budget_status(29, 29.2) == "ok"
    assert classify_budget_status(30, 30.2) == "ok"  # active count limit doesn't fail active status, it only blocks starting new ones
    assert classify_budget_status(60, 60.2) == "rate_limit_budget_exceeded"
