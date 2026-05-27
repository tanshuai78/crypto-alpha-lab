from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from loguru import logger

from configs.base import TREND_REGIME_WATCH_SYMBOLS


def binance_symbol_from_pair(pair: str) -> str:
    return pair.replace("/", "").upper()


def build_binance_fapi_url(*, base_url: str, path: str, params: dict[str, str] | None = None) -> str:
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    if not params:
        return f"{normalized_base}{normalized_path}"
    return f"{normalized_base}{normalized_path}?{urlencode(params)}"


def fetch_json_url(url: str, *, timeout_sec: float) -> Any:
    request = Request(url, headers={"User-Agent": "crypto-alpha-lab/trend-regime-rows"})
    with urlopen(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_value = sum(values) / len(values)
    variance = sum((value - mean_value) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def _hour_bucket(timestamp_ms: int) -> int:
    return timestamp_ms // 3_600_000


def _oi_by_bucket(oi_hist: list[dict[str, Any]]) -> dict[int, float]:
    mapping: dict[int, float] = {}
    for item in oi_hist:
        ts = int(_number_or_none(item.get("timestamp")) or 0)
        oi = _number_or_none(item.get("sumOpenInterest"))
        if ts <= 0 or oi is None:
            continue
        mapping[_hour_bucket(ts)] = oi
    return mapping


def _funding_state(last_funding_rate: float) -> str:
    if last_funding_rate > 0.0005:
        return "positive_extreme"
    if last_funding_rate < -0.0005:
        return "negative_extreme"
    return "neutral"


def build_symbol_market_rows(
    *,
    pair: str,
    symbol_payload: dict[str, Any],
    now_ms: int,
) -> list[dict[str, Any]]:
    klines = list(symbol_payload.get("klines") or [])
    oi_hist = list(symbol_payload.get("oi_hist") or [])
    premium = dict(symbol_payload.get("premium") or {})
    book_ticker = dict(symbol_payload.get("book_ticker") or {})

    if len(klines) < 25:
        return []

    oi_bucket = _oi_by_bucket(oi_hist)
    last_funding_rate = _number_or_none(premium.get("lastFundingRate")) or 0.0

    bid = _number_or_none(book_ticker.get("bidPrice")) or 0.0
    ask = _number_or_none(book_ticker.get("askPrice")) or 0.0
    if bid > 0 and ask > 0 and (bid + ask) > 0:
        spread_bps = (ask - bid) / ((ask + bid) / 2.0) * 10_000.0
    else:
        spread_bps = 6.0
    estimated_slippage_bps = max(2.0, min(7.5, spread_bps * 1.5))

    closes: list[float] = []
    quote_volumes: list[float] = []
    close_times: list[int] = []
    for kline in klines:
        close_time = int(_number_or_none(kline[6]) or 0)
        close_price = _number_or_none(kline[4])
        quote_volume = _number_or_none(kline[7])
        if close_time <= 0 or close_price is None or quote_volume is None:
            continue
        close_times.append(close_time)
        closes.append(close_price)
        quote_volumes.append(quote_volume)

    if len(closes) < 25:
        return []

    rows: list[dict[str, Any]] = []
    for idx in range(24, len(closes)):
        close_time = close_times[idx]
        price = closes[idx]
        prev_price = closes[idx - 1]
        if prev_price <= 0:
            continue

        bucket = _hour_bucket(close_time)
        open_interest = oi_bucket.get(bucket)
        prev_open_interest = oi_bucket.get(bucket - 1)
        if open_interest is None or prev_open_interest is None or prev_open_interest <= 0:
            continue

        return_1h_pct = (price / prev_price - 1.0) * 100.0
        vol_1h_pct = abs(return_1h_pct)

        abs_returns: list[float] = []
        start_idx = max(1, idx - 24 * 30)
        for j in range(start_idx, idx + 1):
            p0 = closes[j - 1]
            p1 = closes[j]
            if p0 <= 0:
                continue
            abs_returns.append(abs((p1 / p0 - 1.0) * 100.0))
        vol_baseline_30d_pct = max(_stddev(abs_returns), 0.0001)

        volume_24h_usdt = sum(quote_volumes[max(0, idx - 23) : idx + 1])
        oi_change_1h_pct = (open_interest / prev_open_interest - 1.0) * 100.0
        data_age_sec = max((now_ms - close_time) / 1000.0, 0.0)

        rows.append(
            {
                "timestamp_ms": close_time,
                "exchange": "binance",
                "symbol": pair,
                "close_price": price,
                "return_1h_pct": return_1h_pct,
                "vol_1h_pct": vol_1h_pct,
                "vol_baseline_30d_pct": vol_baseline_30d_pct,
                "open_interest": open_interest,
                "oi_change_1h_pct": oi_change_1h_pct,
                "liquidation_notional_1h_usdt": None,
                "volume_24h_usdt": volume_24h_usdt,
                "estimated_spread_bps": spread_bps,
                "estimated_slippage_bps": estimated_slippage_bps,
                "funding_state": _funding_state(last_funding_rate),
                "data_age_sec": data_age_sec,
            }
        )

    return rows


def build_market_rows_from_payloads(
    symbol_payloads: dict[str, dict[str, Any]],
    *,
    now_ms: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pair, payload in symbol_payloads.items():
        rows.extend(build_symbol_market_rows(pair=pair, symbol_payload=payload, now_ms=now_ms))
    rows.sort(key=lambda item: (int(item.get("timestamp_ms", 0)), str(item.get("symbol") or "")))
    return rows


def write_rows_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda item: (int(item.get("timestamp_ms", 0)), str(item.get("symbol") or "")))
    with path.open("w", encoding="utf-8") as handle:
        for row in ordered:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def fetch_symbol_payload(
    *,
    pair: str,
    base_url: str,
    timeout_sec: float,
    kline_limit: int,
    oi_limit: int,
) -> dict[str, Any]:
    symbol = binance_symbol_from_pair(pair)
    klines_url = build_binance_fapi_url(
        base_url=base_url,
        path="/fapi/v1/klines",
        params={"symbol": symbol, "interval": "1h", "limit": str(kline_limit)},
    )
    # Binance openInterestHist max limit is 500; cap silently to avoid HTTP 400.
    effective_oi_limit = min(oi_limit, 500)
    oi_url = build_binance_fapi_url(
        base_url=base_url,
        path="/futures/data/openInterestHist",
        params={"symbol": symbol, "period": "1h", "limit": str(effective_oi_limit)},
    )
    premium_url = build_binance_fapi_url(
        base_url=base_url,
        path="/fapi/v1/premiumIndex",
        params={"symbol": symbol},
    )
    book_url = build_binance_fapi_url(
        base_url=base_url,
        path="/fapi/v1/ticker/bookTicker",
        params={"symbol": symbol},
    )

    return {
        "klines": fetch_json_url(klines_url, timeout_sec=timeout_sec),
        "oi_hist": fetch_json_url(oi_url, timeout_sec=timeout_sec),
        "premium": fetch_json_url(premium_url, timeout_sec=timeout_sec),
        "book_ticker": fetch_json_url(book_url, timeout_sec=timeout_sec),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build trend regime Phase1A market rows JSONL")
    parser.add_argument("--output", default="data/trend_regime_phase1a_rows.jsonl")
    parser.add_argument("--symbols", nargs="*", default=list(TREND_REGIME_WATCH_SYMBOLS))
    parser.add_argument("--max-iterations", type=int, default=1)
    parser.add_argument("--poll-interval-sec", type=float, default=60.0)
    parser.add_argument("--forever", action="store_true")
    parser.add_argument("--binance-fapi-base-url", default="https://fapi.binance.com")
    parser.add_argument("--http-timeout-sec", type=float, default=15.0)
    parser.add_argument("--kline-limit", type=int, default=800)
    parser.add_argument("--oi-limit", type=int, default=500)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    pairs = tuple(str(item) for item in args.symbols if str(item))
    if not pairs:
        logger.error("no symbols configured")
        return 2

    iteration = 0
    output_path = Path(args.output)

    while args.forever or iteration < args.max_iterations:
        started_at = time.time()
        now_ms = int(started_at * 1000)

        payloads: dict[str, dict[str, Any]] = {}
        for pair in pairs:
            try:
                payloads[pair] = fetch_symbol_payload(
                    pair=pair,
                    base_url=args.binance_fapi_base_url,
                    timeout_sec=args.http_timeout_sec,
                    kline_limit=args.kline_limit,
                    oi_limit=args.oi_limit,
                )
            except Exception as exc:
                logger.warning("trend_regime_market_rows_fetch_error pair={} reason={}", pair, exc)

        rows = build_market_rows_from_payloads(payloads, now_ms=now_ms)
        write_rows_jsonl(output_path, rows)
        logger.info(
            "trend_regime_market_rows_written rows={} symbols={} output={}",
            len(rows),
            len(payloads),
            output_path,
        )

        iteration += 1
        if not args.forever and iteration >= args.max_iterations:
            break

        elapsed = time.time() - started_at
        sleep_sec = max(float(args.poll_interval_sec) - elapsed, 0.0)
        if sleep_sec > 0.0:
            time.sleep(sleep_sec)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
