from __future__ import annotations

from collections import Counter, defaultdict, deque
from urllib.parse import urlencode
import json
from typing import Any, Callable
from urllib.request import Request, urlopen

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


def binance_symbol_from_pair(pair: str) -> str:
    return pair.replace("/", "")


def build_binance_fapi_url(*, base_url: str, path: str, params: dict[str, str] | None = None) -> str:
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    if not params:
        return f"{normalized_base}{normalized_path}"
    return f"{normalized_base}{normalized_path}?{urlencode(params)}"


UrlOpen = Callable[..., Any]


def fetch_json_url(url: str, *, timeout_sec: float, opener: UrlOpen = urlopen) -> Any:
    request = Request(url, headers={"User-Agent": "crypto-alpha-lab/phase1a-watchlist"})
    with opener(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def find_premium_item(items: list[dict] | dict, binance_symbol: str) -> dict | None:
    if isinstance(items, dict):
        if items.get("symbol") == binance_symbol:
            return items
        return None
    for item in items:
        if item.get("symbol") == binance_symbol:
            return item
    return None


def parse_open_interest(payload: dict) -> float:
    return float(payload["openInterest"])


class OpenInterestWindow:
    def __init__(self, *, lookback_sec: int) -> None:
        self._lookback_ms = lookback_sec * 1000
        self._history: dict[str, deque[tuple[int, float]]] = defaultdict(deque)

    def append(self, symbol: str, *, timestamp_ms: int, open_interest: float) -> None:
        self._history[symbol].append((timestamp_ms, open_interest))
        self._prune(symbol, now_ms=timestamp_ms)

    def change_pct(self, symbol: str, *, now_ms: int, current_open_interest: float) -> float | None:
        self._prune(symbol, now_ms=now_ms)
        if not self._history[symbol]:
            return None
        oldest_ts, oldest_value = self._history[symbol][0]
        if now_ms - oldest_ts < self._lookback_ms or oldest_value <= 0:
            return None
        return ((current_open_interest - oldest_value) / oldest_value) * 100

    def _prune(self, symbol: str, *, now_ms: int) -> None:
        cutoff_ms = now_ms - self._lookback_ms
        while len(self._history[symbol]) > 1 and self._history[symbol][1][0] <= cutoff_ms:
            self._history[symbol].popleft()




