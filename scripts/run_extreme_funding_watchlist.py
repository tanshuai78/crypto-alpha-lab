from __future__ import annotations

from collections import Counter

PUBLIC_SNAPSHOT_FIELDS = {
    "symbol",
    "exchange",
    "timestamp_ms",
    "mark_price",
    "index_price",
    "premium_index",
    "estimated_funding_rate",
    "next_funding_time_ms",
    "open_interest",
    "oi_change_1h_pct",
    "volume_24h_usdt",
    "mark_data_age_sec",
    "oi_data_age_sec",
}


def should_poll(*, last_poll_ts: float, now_ts: float, interval_sec: int) -> bool:
    return now_ts - last_poll_ts >= interval_sec


def summarize_reject_counts(reasons: list[str]) -> dict[str, int]:
    return dict(Counter(reasons))


def build_snapshot(raw: dict) -> dict:
    return {key: raw.get(key) for key in PUBLIC_SNAPSHOT_FIELDS}
