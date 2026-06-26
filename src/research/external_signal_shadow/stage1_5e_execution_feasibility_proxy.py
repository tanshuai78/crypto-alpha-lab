from typing import Any, Dict, List


def compute_entry_proxy_metrics(
    symbol: str,
    entry_time_ms: int,
    bars: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compute execution proxy metrics for a single candidate based on 15m historical klines.

    Parameters:
      symbol: The trading pair symbol.
      entry_time_ms: The entry timestamp in milliseconds.
      bars: List of 15m kline dicts. Each dict must contain:
        "bar_start_ms", "open", "high", "low", "close", "quote_volume"
    """
    # Sort bars by start time to be safe
    sorted_bars = sorted(bars, key=lambda b: b["bar_start_ms"])

    # 1. Find entry bar: first bar where bar_start_ms >= entry_time_ms
    entry_idx = -1
    for i, bar in enumerate(sorted_bars):
        if bar["bar_start_ms"] >= entry_time_ms:
            entry_idx = i
            break

    if entry_idx == -1:
        return {
            "symbol": symbol,
            "entry_time_ms": entry_time_ms,
            "entry_bar_found": False,
            "historical_proxy_status": "missing_entry_bar"
        }

    entry_bar = sorted_bars[entry_idx]

    # Ensure we have at least 16 forward bars (index entry_idx to entry_idx + 15) to calculate 4h forward metrics
    if len(sorted_bars) - entry_idx < 16:
        return {
            "symbol": symbol,
            "entry_time_ms": entry_time_ms,
            "entry_bar_found": False,
            "historical_proxy_status": "insufficient_forward_bars"
        }

    # Forward windows
    forward_1h_bars = sorted_bars[entry_idx : entry_idx + 4]
    forward_4h_bars = sorted_bars[entry_idx : entry_idx + 16]

    # Compute ranges in bps
    entry_bar_range_bps = (entry_bar["high"] - entry_bar["low"]) / entry_bar["open"] * 10_000.0
    entry_bar_close_to_open_bps = (entry_bar["close"] - entry_bar["open"]) / entry_bar["open"] * 10_000.0

    max_high_1h = max(b["high"] for b in forward_1h_bars)
    min_low_1h = min(b["low"] for b in forward_1h_bars)
    entry_1h_range_bps = (max_high_1h / min_low_1h - 1.0) * 10_000.0

    max_high_4h = max(b["high"] for b in forward_4h_bars)
    min_low_4h = min(b["low"] for b in forward_4h_bars)
    entry_4h_range_bps = (max_high_4h / min_low_4h - 1.0) * 10_000.0

    # Compute quote volume
    post_entry_1h_quote_volume_usdt = sum(b["quote_volume"] for b in forward_1h_bars)
    post_entry_4h_quote_volume_usdt = sum(b["quote_volume"] for b in forward_4h_bars)

    # Pre-entry 24h window: [entry_time_ms - 24h, entry_time_ms)
    pre_start = entry_time_ms - 24 * 60 * 60 * 1000
    pre_entry_bars = [b for b in sorted_bars if pre_start <= b["bar_start_ms"] < entry_time_ms]

    # Quote volume in pre-entry 24h
    pre_entry_24h_quote_volume_usdt = sum(b["quote_volume"] for b in pre_entry_bars)

    # Construct 24 hourly buckets for pre-entry volume
    hourly_volumes = []
    hour_ms = 60 * 60 * 1000
    for h in range(24):
        h_start = pre_start + h * hour_ms
        h_end = h_start + hour_ms
        vol = sum(b["quote_volume"] for b in pre_entry_bars if h_start <= b["bar_start_ms"] < h_end)
        hourly_volumes.append(vol)

    if hourly_volumes:
        sorted_hourly = sorted(hourly_volumes)
        median_same_symbol_pre_entry_24h_hourly_volume = sorted_hourly[12]  # median of 24 items
    else:
        median_same_symbol_pre_entry_24h_hourly_volume = 0.0

    if median_same_symbol_pre_entry_24h_hourly_volume > 0:
        volume_collapse_ratio_1h = post_entry_1h_quote_volume_usdt / median_same_symbol_pre_entry_24h_hourly_volume
    else:
        volume_collapse_ratio_1h = 0.0

    result = {
        "symbol": symbol,
        "entry_time_ms": entry_time_ms,
        "entry_bar_found": True,
        "historical_proxy_status": "proxy_computed",
        "entry_bar_range_bps": entry_bar_range_bps,
        "entry_bar_close_to_open_bps": entry_bar_close_to_open_bps,
        "entry_1h_range_bps": entry_1h_range_bps,
        "entry_4h_range_bps": entry_4h_range_bps,
        "pre_entry_24h_quote_volume_usdt": pre_entry_24h_quote_volume_usdt,
        "post_entry_1h_quote_volume_usdt": post_entry_1h_quote_volume_usdt,
        "post_entry_4h_quote_volume_usdt": post_entry_4h_quote_volume_usdt,
        "median_same_symbol_pre_entry_24h_hourly_volume": median_same_symbol_pre_entry_24h_hourly_volume,
        "volume_collapse_ratio_1h": volume_collapse_ratio_1h,
    }

    return result
