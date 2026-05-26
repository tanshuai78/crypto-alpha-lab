from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from loguru import logger

from configs.base import TREND_REGIME_WATCH_SYMBOLS


def _symbol_key(symbol: str) -> str:
    return symbol.replace("/", "").upper()


def build_force_order_stream_url(symbols: tuple[str, ...], *, base_url: str = "wss://fstream.binance.com") -> str:
    streams = "/".join(f"{_symbol_key(symbol).lower()}@forceOrder" for symbol in symbols)
    return f"{base_url.rstrip('/')}/stream?streams={streams}"


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


def parse_force_order_notional_event(message: dict[str, Any]) -> tuple[str, int, float] | None:
    payload = message.get("data") if isinstance(message.get("data"), dict) else message
    if not isinstance(payload, dict):
        return None
    if payload.get("e") != "forceOrder":
        return None

    order = payload.get("o")
    if not isinstance(order, dict):
        return None

    symbol = str(order.get("s") or "").upper()
    if not symbol:
        return None

    event_time_ms = int(_number_or_none(payload.get("E")) or _number_or_none(order.get("T")) or 0)
    if event_time_ms <= 0:
        return None

    quantity = (
        _number_or_none(order.get("z"))
        or _number_or_none(order.get("l"))
        or _number_or_none(order.get("q"))
        or 0.0
    )
    price = (
        _number_or_none(order.get("ap"))
        or _number_or_none(order.get("p"))
        or 0.0
    )
    if quantity <= 0.0 or price <= 0.0:
        return None

    return symbol, event_time_ms, round(quantity * price, 10)


class RollingLiquidationAccumulator:
    def __init__(self, *, window_ms: int) -> None:
        self.window_ms = window_ms
        self._events: dict[str, deque[tuple[int, float]]] = defaultdict(deque)

    def add_event(self, symbol: str, *, event_time_ms: int, notional_usdt: float) -> None:
        self._events[symbol].append((event_time_ms, notional_usdt))
        self._prune_symbol(symbol, now_ms=event_time_ms)

    def snapshot_totals(self, *, now_ms: int) -> dict[str, float]:
        totals: dict[str, float] = {}
        for symbol in list(self._events.keys()):
            self._prune_symbol(symbol, now_ms=now_ms)
            if not self._events[symbol]:
                continue
            totals[symbol] = round(sum(v for _, v in self._events[symbol]), 10)
        return totals

    def _prune_symbol(self, symbol: str, *, now_ms: int) -> None:
        cutoff = now_ms - self.window_ms
        events = self._events[symbol]
        while events and events[0][0] < cutoff:
            events.popleft()


def write_liquidation_cache_json(path: Path, symbol_notional_map: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(symbol_notional_map, handle, ensure_ascii=False, sort_keys=True)


def should_stop(*, start_ts: float, now_ts: float, max_seconds: int) -> bool:
    if max_seconds <= 0:
        return False
    return now_ts - start_ts >= float(max_seconds)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Binance forceOrder stream and write 1h liquidation cache")
    parser.add_argument("--output", default="data/trend_regime_liquidation_cache.json")
    parser.add_argument("--window-sec", type=int, default=3600)
    parser.add_argument("--flush-interval-sec", type=float, default=10.0)
    parser.add_argument("--max-seconds", type=int, default=0, help="0 means run forever")
    parser.add_argument("--ws-base-url", default="wss://fstream.binance.com")
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=list(TREND_REGIME_WATCH_SYMBOLS),
        help="Symbol list like BTC/USDT ETH/USDT",
    )
    return parser.parse_args(argv)


async def run_collector(args: argparse.Namespace) -> int:
    try:
        import websockets
    except ImportError:
        logger.error("missing dependency: websockets. run with: uv run --with websockets python scripts/collect_trend_regime_force_orders.py ...")
        return 2

    symbols = tuple(str(s) for s in args.symbols if str(s))
    if not symbols:
        logger.error("no symbols configured for forceOrder collector")
        return 2

    url = build_force_order_stream_url(symbols, base_url=args.ws_base_url)
    accumulator = RollingLiquidationAccumulator(window_ms=int(args.window_sec * 1000))
    output_path = Path(args.output)

    start_ts = time.time()
    last_flush_ts = 0.0
    message_count = 0
    accepted_count = 0

    logger.info("force_order_collector_start url={} output={} symbols={}", url, output_path, symbols)

    while True:
        if should_stop(start_ts=start_ts, now_ts=time.time(), max_seconds=args.max_seconds):
            break
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                while True:
                    now = time.time()
                    now_ms = int(now * 1000)

                    recv_timeout = max(0.2, float(args.flush_interval_sec))
                    raw: str | None = None
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
                    except asyncio.TimeoutError:
                        raw = None

                    if raw is not None:
                        message_count += 1
                        try:
                            message = json.loads(raw)
                        except json.JSONDecodeError:
                            message = None

                        if isinstance(message, dict):
                            parsed = parse_force_order_notional_event(message)
                            if parsed is not None:
                                symbol, event_time_ms, notional = parsed
                                accumulator.add_event(symbol, event_time_ms=event_time_ms, notional_usdt=notional)
                                accepted_count += 1

                    if now - last_flush_ts >= float(args.flush_interval_sec):
                        totals = accumulator.snapshot_totals(now_ms=now_ms)
                        write_liquidation_cache_json(output_path, totals)
                        logger.info(
                            "force_order_collector_flush messages={} accepted={} symbols_with_liq={}",
                            message_count,
                            accepted_count,
                            len(totals),
                        )
                        last_flush_ts = now

                    if should_stop(start_ts=start_ts, now_ts=now, max_seconds=args.max_seconds):
                        break
        except Exception as exc:
            logger.warning("force_order_collector_reconnect reason={}", exc)
            await asyncio.sleep(2.0)

    totals = accumulator.snapshot_totals(now_ms=int(time.time() * 1000))
    write_liquidation_cache_json(output_path, totals)
    logger.info(
        "force_order_collector_stop messages={} accepted={} symbols_with_liq={} output={}",
        message_count,
        accepted_count,
        len(totals),
        output_path,
    )
    return 0


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return await run_collector(args)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
