from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from configs import base

INTERVAL_15M_MS = 15 * 60 * 1000
JsonFetcher = Callable[[str], list[list[Any]]]


def build_klines_url(
    *,
    base_url: str,
    symbol: str,
    start_ms: int,
    end_ms: int,
    limit: int,
) -> str:
    query = urlencode({
        "symbol": symbol,
        "interval": base.EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_INTERVAL,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit,
    })
    return f"{base_url.rstrip('/')}{base.EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_KLINES_PATH}?{query}"


def parse_spot_kline_row(symbol: str, row: list[Any]) -> dict[str, float | int | str]:
    if len(row) < 8:
        raise ValueError("kline row must contain at least 8 fields")
    open_time = int(row[0])
    close_time = int(row[6])
    expected_close_time = open_time + INTERVAL_15M_MS - 1
    if close_time != expected_close_time:
        raise ValueError(f"kline close time mismatch: expected {expected_close_time}, got {close_time}")
    return {
        "symbol": symbol,
        "bar_start_ms": open_time,
        "bar_end_ms": open_time + INTERVAL_15M_MS,
        "open_price": float(row[1]),
        "high_price": float(row[2]),
        "low_price": float(row[3]),
        "close_price": float(row[4]),
        "quote_volume": float(row[7]),
    }


def fetch_json_public(url: str, *, timeout_sec: float) -> list[list[Any]]:
    request = Request(url, headers={"User-Agent": "crypto-alpha-lab-stage1-3-binance-proxy/0.1"})
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Binance public kline request failed with HTTP {exc.code}: {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Binance public kline request failed: {exc.reason}") from exc
    if not isinstance(payload, list):
        raise RuntimeError("Binance kline response must be a list")
    return payload


def collect_symbol_bars(
    *,
    symbol: str,
    start_ms: int,
    end_ms: int,
    fetch_json: JsonFetcher,
    base_url: str,
    limit: int,
    request_sleep_sec: float,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    seen_open_times: set[int] = set()
    cursor = start_ms
    while cursor < end_ms:
        url = build_klines_url(base_url=base_url, symbol=symbol, start_ms=cursor, end_ms=end_ms, limit=limit)
        payload = fetch_json(url)
        if not payload:
            break

        last_open_time: int | None = None
        for raw_row in payload:
            parsed = parse_spot_kline_row(symbol, raw_row)
            open_time = int(parsed["bar_start_ms"])
            if open_time < start_ms or open_time >= end_ms:
                continue
            if open_time in seen_open_times:
                continue
            seen_open_times.add(open_time)
            rows.append(parsed)
            last_open_time = open_time

        if last_open_time is None:
            break
        next_cursor = last_open_time + INTERVAL_15M_MS
        if next_cursor <= cursor:
            raise RuntimeError(f"pagination made no progress for {symbol} at {cursor}")
        cursor = next_cursor
        if len(payload) < limit:
            break
        if request_sleep_sec > 0:
            time.sleep(request_sleep_sec)

    rows.sort(key=lambda item: int(item["bar_start_ms"]))
    return rows


def _load_mock_fetcher(path: Path) -> JsonFetcher:
    by_symbol = json.loads(path.read_text())

    def fetch_json(url: str) -> list[list[Any]]:
        marker = "symbol="
        if marker not in url:
            return []
        symbol = url.split(marker, 1)[1].split("&", 1)[0]
        return list(by_symbol.get(symbol, []))

    return fetch_json


def _parse_symbols(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return base.EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_SYMBOLS
    return tuple(item.strip().upper() for item in raw.split(",") if item.strip())


def _default_window_ms(days: int) -> tuple[int, int]:
    now = datetime.now(tz=UTC)
    end = int(now.timestamp() * 1000)
    end -= end % INTERVAL_15M_MS
    start = int((now - timedelta(days=days)).timestamp() * 1000)
    start -= start % INTERVAL_15M_MS
    return start, end


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Stage 1.3 Binance proxy 15m OHLCV bars JSONL")
    parser.add_argument("--output", required=True)
    parser.add_argument("--symbols", default=None)
    parser.add_argument("--days", type=int, default=base.EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_PREFERRED)
    parser.add_argument("--start-ms", type=int, default=None)
    parser.add_argument("--end-ms", type=int, default=None)
    parser.add_argument("--base-url", default=base.EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_BASE_URL)
    parser.add_argument("--mock-klines-json", default=None)
    parser.add_argument("--live-public-readonly", action="store_true")
    args = parser.parse_args(argv)

    if args.mock_klines_json and args.live_public_readonly:
        print("--mock-klines-json and --live-public-readonly are mutually exclusive", file=sys.stderr)
        return 1
    if not args.mock_klines_json and not args.live_public_readonly:
        print("Refusing network access without --live-public-readonly", file=sys.stderr)
        return 1

    if args.start_ms is None or args.end_ms is None:
        start_ms, end_ms = _default_window_ms(args.days)
    else:
        start_ms, end_ms = args.start_ms, args.end_ms
    if end_ms <= start_ms:
        print("end must be greater than start", file=sys.stderr)
        return 1

    symbols = _parse_symbols(args.symbols)
    fetcher: JsonFetcher
    if args.mock_klines_json:
        fetcher = _load_mock_fetcher(Path(args.mock_klines_json))
    else:
        def fetcher(url: str) -> list[list[Any]]:
            return fetch_json_public(url, timeout_sec=base.EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_TIMEOUT_SEC)

    all_rows: list[dict[str, float | int | str]] = []
    try:
        for symbol in symbols:
            symbol_rows = collect_symbol_bars(
                symbol=symbol,
                start_ms=start_ms,
                end_ms=end_ms,
                fetch_json=fetcher,
                base_url=args.base_url,
                limit=base.EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_KLINES_LIMIT,
                request_sleep_sec=base.EXTERNAL_SIGNAL_STAGE1_3_BINANCE_PROXY_REQUEST_SLEEP_SEC,
            )
            if not symbol_rows:
                raise RuntimeError(f"no kline rows returned for {symbol}")
            all_rows.extend(symbol_rows)
    except Exception as exc:
        print(f"Failed to build Binance proxy bars: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(json.dumps(row, separators=(",", ":")) for row in all_rows) + "\n")
    print(f"wrote {len(all_rows)} bars to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
