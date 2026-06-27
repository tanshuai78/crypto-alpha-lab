from configs import base


def estimate_requests_per_min(
    active_count: int,
    depth_requests_per_symbol_per_poll: int = 1,
    poll_interval_sec: int = 60,
    exchangeinfo_refresh_requests_per_min: float = 0.2
) -> float:
    polls_per_min = 60.0 / poll_interval_sec
    requests_per_poll = active_count * depth_requests_per_symbol_per_poll
    return requests_per_poll * polls_per_min + exchangeinfo_refresh_requests_per_min


def can_start_new_observation(active_count: int, estimated_requests_per_min: float) -> bool:
    max_active = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_ACTIVE_EVENT_SYMBOLS
    max_reqs = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_DEPTH_REQUESTS_PER_MINUTE

    if active_count >= max_active:
        return False
    if estimated_requests_per_min > max_reqs:
        return False
    return True


def classify_budget_status(active_count: int, estimated_requests_per_min: float) -> str:
    max_reqs = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_DEPTH_REQUESTS_PER_MINUTE
    if estimated_requests_per_min > max_reqs:
        return "rate_limit_budget_exceeded"
    return "ok"
