from __future__ import annotations

from collections import Counter, defaultdict, deque
from urllib.parse import urlencode
import json
from typing import Any, Callable
from urllib.request import Request, urlopen
from strategies.extreme_funding.scanner import ExtremeFundingWatchlistScanner
import argparse
import asyncio
import time
from json import JSONDecodeError
from pathlib import Path
from urllib.error import HTTPError, URLError
from loguru import logger

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


def build_raw_snapshot_from_public_data(
    *,
    pair: str,
    exchange: str,
    timestamp_ms: int,
    premium_item: dict,
    open_interest: float | None,
    oi_change_1h_pct: float | None,
    mark_data_age_sec: float,
    oi_data_age_sec: float,
) -> dict:
    mark_price = float(premium_item["markPrice"])
    index_price = float(premium_item["indexPrice"])
    premium_index = (mark_price - index_price) / index_price if index_price > 0 else 0.0
    return {
        "symbol": pair,
        "exchange": exchange,
        "timestamp_ms": timestamp_ms,
        "mark_price": mark_price,
        "index_price": index_price,
        "premium_index": premium_index,
        "estimated_funding_rate": float(premium_item.get("lastFundingRate", 0.0)),
        "next_funding_time_ms": int(premium_item.get("nextFundingTime", 0)),
        "open_interest": open_interest,
        "oi_change_1h_pct": oi_change_1h_pct,
        "volume_24h_usdt": None,
        "mark_data_age_sec": mark_data_age_sec,
        "oi_data_age_sec": oi_data_age_sec,
    }


def run_watchlist_poll_once(
    *,
    pairs: tuple[str, ...],
    scanner: ExtremeFundingWatchlistScanner,
    oi_window: OpenInterestWindow,
    timestamp_ms: int,
    premium_payload: list[dict] | dict,
    oi_payloads: dict[str, dict],
    oi_data_age_sec: float,
) -> dict[str, Any]:
    events = []
    reject_reasons = []
    snapshots = []

    for pair in pairs:
        binance_symbol = binance_symbol_from_pair(pair)
        premium_item = find_premium_item(premium_payload, binance_symbol)
        if premium_item is None:
            reject_reasons.append("missing_premium")
            continue

        oi_payload = oi_payloads.get(binance_symbol)
        open_interest = parse_open_interest(oi_payload) if oi_payload else None
        oi_change = None
        if open_interest is not None:
            # Calculate against the previous retained value before appending current OI.
            oi_change = oi_window.change_pct(
                pair,
                now_ms=timestamp_ms,
                current_open_interest=open_interest,
            )
            oi_window.append(pair, timestamp_ms=timestamp_ms, open_interest=open_interest)

        raw = build_raw_snapshot_from_public_data(
            pair=pair,
            exchange="binance",
            timestamp_ms=timestamp_ms,
            premium_item=premium_item,
            open_interest=open_interest,
            oi_change_1h_pct=oi_change,
            mark_data_age_sec=0.0,
            oi_data_age_sec=oi_data_age_sec if oi_payload else 999999.0,
        )
        snapshot = build_snapshot(raw)
        snapshots.append(snapshot)
        result = scanner.classify(snapshot)
        if result.event is not None:
            events.append(result.event)
        elif result.reject_reason is not None:
            reject_reasons.append(result.reject_reason)

    return {"events": events, "reject_reasons": reject_reasons, "snapshots": snapshots}


from configs.base import (
    EXTREME_FUNDING_BINANCE_FAPI_BASE_URL,
    EXTREME_FUNDING_EVENT_LOG_JSONL,
    EXTREME_FUNDING_HEARTBEAT_INTERVAL_SEC,
    EXTREME_FUNDING_HTTP_TIMEOUT_SEC,
    EXTREME_FUNDING_LOCAL_DRY_RUN_MAX_ITERATIONS,
    EXTREME_FUNDING_LOOP_ERROR_BACKOFF_SEC,
    EXTREME_FUNDING_MARK_DATA_POLL_INTERVAL_SEC,
    EXTREME_FUNDING_OI_CHANGE_LOOKBACK_SEC,
    EXTREME_FUNDING_OI_POLL_INTERVAL_SEC,
    EXTREME_FUNDING_WATCH_SYMBOLS,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phase 1A extreme funding watchlist daemon.")
    parser.add_argument("--forever", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-iterations", type=int, default=EXTREME_FUNDING_LOCAL_DRY_RUN_MAX_ITERATIONS)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--poll-interval-sec", type=float, default=float(EXTREME_FUNDING_MARK_DATA_POLL_INTERVAL_SEC))
    args = parser.parse_args(argv)
    if args.once:
        args.max_iterations = 1
        args.poll_interval_sec = 0.0
    return args


def classify_loop_exception(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, HTTPError):
        return "watchlist_http_error", f"status={exc.code} detail={exc.reason}"
    if isinstance(exc, URLError):
        return "watchlist_url_error", f"detail={exc.reason}"
    if isinstance(exc, JSONDecodeError):
        return "watchlist_json_error", f"detail={exc}"
    if isinstance(exc, KeyError):
        return "watchlist_schema_error", f"missing={exc}"
    return "watchlist_loop_error", f"type={type(exc).__name__} detail={exc}"


def should_refresh_oi(*, last_fetch_ts: float | None, now_ts: float, interval_sec: int) -> bool:
    if last_fetch_ts is None:
        return True
    return now_ts - last_fetch_ts >= interval_sec


def oi_data_age_sec(*, last_fetch_ts: float | None, now_ts: float) -> float:
    if last_fetch_ts is None:
        return 999999.0
    return now_ts - last_fetch_ts


def append_jsonl(filepath: Path, data: dict) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, default=str) + "\n")


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    scanner = ExtremeFundingWatchlistScanner()
    oi_window = OpenInterestWindow(lookback_sec=EXTREME_FUNDING_OI_CHANGE_LOOKBACK_SEC)
    iteration = 0
    last_heartbeat = 0.0

    oi_payload_cache: dict[str, dict] = {}
    last_oi_fetch_ts: float | None = None

    event_log_path = Path(args.data_root) / EXTREME_FUNDING_EVENT_LOG_JSONL

    while args.forever or iteration < args.max_iterations:
        try:
            now_ts = time.time()
            now_ms = int(now_ts * 1000)

            premium_url = build_binance_fapi_url(
                base_url=EXTREME_FUNDING_BINANCE_FAPI_BASE_URL,
                path="/fapi/v1/premiumIndex",
            )
            premium_payload = fetch_json_url(premium_url, timeout_sec=EXTREME_FUNDING_HTTP_TIMEOUT_SEC)

            if should_refresh_oi(
                last_fetch_ts=last_oi_fetch_ts,
                now_ts=now_ts,
                interval_sec=EXTREME_FUNDING_OI_POLL_INTERVAL_SEC,
            ):
                new_oi_payloads = {}
                for pair in EXTREME_FUNDING_WATCH_SYMBOLS:
                    symbol = binance_symbol_from_pair(pair)
                    oi_url = build_binance_fapi_url(
                        base_url=EXTREME_FUNDING_BINANCE_FAPI_BASE_URL,
                        path="/fapi/v1/openInterest",
                        params={"symbol": symbol},
                    )
                    try:
                        new_oi_payloads[symbol] = fetch_json_url(oi_url, timeout_sec=EXTREME_FUNDING_HTTP_TIMEOUT_SEC)
                    except Exception as e:
                        logger.warning(f"Failed to fetch OI for {symbol}: {e}")
                        if symbol in oi_payload_cache:
                            new_oi_payloads[symbol] = oi_payload_cache[symbol]
                
                oi_payload_cache = new_oi_payloads
                last_oi_fetch_ts = now_ts

            oi_age = oi_data_age_sec(last_fetch_ts=last_oi_fetch_ts, now_ts=now_ts)

            result = run_watchlist_poll_once(
                pairs=EXTREME_FUNDING_WATCH_SYMBOLS,
                scanner=scanner,
                oi_window=oi_window,
                timestamp_ms=now_ms,
                premium_payload=premium_payload,
                oi_payloads=oi_payload_cache,
                oi_data_age_sec=oi_age,
            )

            if result["events"]:
                for event in result["events"]:
                    logger.info(f"watch_event={event}")
                    append_jsonl(event_log_path, {"type": "watch_event", "event": event.__dict__})

            if should_poll(
                last_poll_ts=last_heartbeat,
                now_ts=now_ts,
                interval_sec=EXTREME_FUNDING_HEARTBEAT_INTERVAL_SEC,
            ):
                logger.info(
                    "heartbeat "
                    f"events={len(result['events'])} "
                    f"rejects={summarize_reject_counts(result['reject_reasons'])}"
                )
                append_jsonl(
                    event_log_path,
                    {
                        "type": "heartbeat_summary",
                        "timestamp_ms": now_ms,
                        "events": len(result["events"]),
                        "reject_counts": summarize_reject_counts(result["reject_reasons"]),
                        "oi_data_age_sec": oi_age,
                    },
                )
                last_heartbeat = now_ts

            iteration += 1
            if not args.forever and iteration >= args.max_iterations:
                break
            await asyncio.sleep(args.poll_interval_sec)
        except Exception as exc:
            err_type, err_detail = classify_loop_exception(exc)
            logger.warning(f"{err_type} {err_detail}")
            iteration += 1
            if not args.forever and iteration >= args.max_iterations:
                break
            await asyncio.sleep(EXTREME_FUNDING_LOOP_ERROR_BACKOFF_SEC)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))







