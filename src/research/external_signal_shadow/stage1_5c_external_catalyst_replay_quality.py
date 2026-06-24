import statistics

from configs import base


def build_price_index(price_bars: list[dict]) -> dict[str, list[dict]]:
    index = {}
    for bar in price_bars:
        symbol = bar["symbol"]
        if symbol not in index:
            index[symbol] = []
        index[symbol].append(bar)
    # Sort each symbol's bars by bar_start_ms
    for symbol in index:
        index[symbol].sort(key=lambda x: x["bar_start_ms"])
    return index


def compute_price_interval_stats(symbol_bars: list[dict]) -> dict:
    if len(symbol_bars) < 2:
        return {
            "median_interval_ms": base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_INTERVAL_MS,
            "p95_interval_ms": base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_INTERVAL_MS,
            "price_interval_supported": True,
        }
    intervals = []
    for i in range(len(symbol_bars) - 1):
        diff = symbol_bars[i + 1]["bar_start_ms"] - symbol_bars[i]["bar_start_ms"]
        intervals.append(diff)

    median_val = statistics.median(intervals)
    p95_val = percentiles(intervals, 95)
    supported = (
        median_val <= base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_INTERVAL_MS
        and p95_val <= base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_P95_MAX_INTERVAL_MS
    )
    return {
        "median_interval_ms": median_val,
        "p95_interval_ms": p95_val,
        "price_interval_supported": supported,
    }


def percentiles(data, pct):
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (len(sorted_data) - 1) * pct / 100.0
    floor_idx = int(idx)
    ceil_idx = min(floor_idx + 1, len(sorted_data) - 1)
    if floor_idx == ceil_idx:
        return float(sorted_data[floor_idx])
    return float(sorted_data[floor_idx] + (idx - floor_idx) * (sorted_data[ceil_idx] - sorted_data[floor_idx]))


def find_first_bar_at_or_after(symbol_bars: list[dict], ts_ms: int) -> dict | None:
    for bar in symbol_bars:
        if bar["bar_start_ms"] >= ts_ms:
            return bar
    return None


def evaluate_event_price_coverage(
    event: dict,
    price_index: dict,
    entry_delay_hours: int,
    forward_windows_hours: tuple[int, ...]
) -> dict:
    symbol = event["symbol"]
    available_at_ms = event["available_at_ms"]
    upstream_allowed = event.get("stage1_5b_replay_candidate_allowed_upstream", False)

    base_report = {
        "stage1_5b_replay_candidate_allowed_upstream": upstream_allowed,
        "price_coverage_gate_passed": False,
        "candidate_allowed_for_close_price_replay": False,
        "candidate_allowed_for_execution_relevance": False,
        "price_history_coverage_verified": False,
        "market_pair_existence_verified": False,
        "liquidity_proxy_pass": False,
        "liquidity_proxy_verified": False,
        "coverage_reject_reason": None,
    }

    if symbol not in price_index:
        base_report["coverage_reject_reason"] = "missing_price_history"
        return base_report

    symbol_bars = price_index[symbol]
    base_report["market_pair_existence_verified"] = True

    # 1. Price interval stats
    stats = compute_price_interval_stats(symbol_bars)
    if not stats["price_interval_supported"]:
        base_report["coverage_reject_reason"] = "price_interval_unsupported"
        return base_report

    # 2. Entry bar
    entry_candidate_time_ms = available_at_ms + entry_delay_hours * 3600_000
    entry_bar = find_first_bar_at_or_after(symbol_bars, entry_candidate_time_ms)
    if not entry_bar:
        base_report["coverage_reject_reason"] = "missing_entry_bar"
        return base_report

    base_report["entry_candidate_time_ms"] = entry_candidate_time_ms
    base_report["entry_bar_start_ms"] = entry_bar["bar_start_ms"]
    base_report["entry_price"] = entry_bar["open"]

    # 3. Forward windows completion
    for window in forward_windows_hours:
        exit_target_ms = entry_bar["bar_start_ms"] + window * 3600_000
        exit_bar = find_first_bar_at_or_after(symbol_bars, exit_target_ms)
        if not exit_bar:
            base_report["coverage_reject_reason"] = "forward_window_incomplete"
            return base_report

    # 4. Min price history before event (30 days)
    min_pre_ms = available_at_ms - base.EXTERNAL_SIGNAL_STAGE1_5C_MIN_PRE_EVENT_PRICE_HISTORY_DAYS * 24 * 3600 * 1000
    if symbol_bars[0]["bar_start_ms"] > min_pre_ms:
        base_report["coverage_reject_reason"] = "insufficient_pre_event_history"
        return base_report

    base_report["price_history_coverage_verified"] = True

    # If we made it here, price coverage is passed
    base_report["price_coverage_gate_passed"] = True
    base_report["candidate_allowed_for_close_price_replay"] = True

    # 5. Liquidity proxy gate
    # sum of quote_volume in the 24h before available_at_ms
    pre_24h_start = available_at_ms - 24 * 3600_000
    vol_24h = 0.0
    for bar in symbol_bars:
        if pre_24h_start <= bar["bar_start_ms"] < available_at_ms:
            vol_24h += bar["quote_volume"]

    base_report["liquidity_proxy_verified"] = True
    if vol_24h >= base.EXTERNAL_SIGNAL_STAGE1_5C_MIN_PRE_EVENT_24H_QUOTE_VOLUME_USDT:
        base_report["liquidity_proxy_pass"] = True
        base_report["candidate_allowed_for_execution_relevance"] = True
    else:
        base_report["liquidity_proxy_pass"] = False
        base_report["candidate_allowed_for_execution_relevance"] = False

    return base_report
